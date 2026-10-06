"""Memory defences: what gets written, and what gets recalled.

Every defence answers two questions:
- review(): should this candidate memory be stored, quarantined, or rejected,
  and does it retire (supersede) older memories?
- recall(): which stored memories go into the model's context for a query?

The baselines below come from prior work, so the thymus gate is measured against
real competition rather than only "no defence":

- allow-all: no defence, what most memory agents ship with.
- user-only: provenance quarantine. Blocks everything that came from tool content
  (≈ MemGauge's PQ policy, arXiv 2608.30177).
- conflict-quarantine: tool content that contradicts something a user stated is
  quarantined (≈ MemGauge's NC policy). Adapted so users can still correct their own facts.
- last-write-wins: the newest memory always replaces the ones it contradicts.
  The naive way to support updates.
- bounded-occupancy: writes everything, but tool-sourced memories may fill at most
  one recall slot (proposed but not built in Utility Under Attack, arXiv 2608.21230).
- label-only: keeps everything and recalls untrusted memories with their source, with no
  rules about updates. The labelling idea of TMA-NM (arXiv 2606.24322) and PPMF
  (arXiv 2607.29167), which use it to gate actions, applied to answers instead.

And the gate this project is about:

- thymus: self/non-self screening. Tool content may add facts but never speak for the
  user; a fact can only be replaced by the user or by the source that stated it; every
  other conflicting or unvetted claim is kept but recalled with an "unverified" label.

Ablations switch off one part of the thymus gate at a time:

- thymus-no-screen: no self/non-self screening; tool content may state preferences or
  instructions in the user's name.
- thymus-any-origin: no same-origin rule; tool content replaces whatever it contradicts.
- thymus-no-labels: same storage decisions, but memories are recalled without labels.
- thymus-hide: decide instead of disclose; a claim that contradicts another source is
  quarantined (hidden) instead of kept with a label.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

from thymus.claims import ClaimClassifier, LLMClaimClassifier
from thymus.conflicts import ConflictDetector, LLMConflictDetector
from thymus.llm import LLM
from thymus.memory import Candidate, Memory, MemoryStore, Trust

Action = Literal["accept", "reject", "quarantine"]


@dataclass(frozen=True)
class Decision:
    action: Action
    reason: str
    supersedes: tuple[int, ...] = ()  # ids of memories to retire if this one is stored
    trust: Trust = "verified"
    contradicts: tuple[int, ...] = ()  # ids this memory disagrees with but does not replace


class Gate:
    name = "base"
    soft_supersede = False  # replaced memories are kept as labelled older versions instead of retired

    def apply_supersedes(self, store: MemoryStore, ids: tuple[int, ...]) -> None:
        if self.soft_supersede:
            store.mark_older(ids)
        else:
            store.retire(ids)

    def review(self, candidate: Candidate, store: MemoryStore) -> Decision:
        return Decision("accept", "no checks")

    def recall(self, query: str, store: MemoryStore, k: int, speaker: str) -> list[Memory]:
        return [memory for memory, _ in store.search(query, k=k)]

    def render(self, memory: Memory, speaker: str) -> str:
        """How a recalled memory appears in the model's context."""
        return f"[turn {memory.created_at}] {memory.text}"

    def background_trust(self, candidate: Candidate) -> Trust | None:
        """Decision for a haystack fact that conflicts with nothing (see thymus.haystack):
        the trust it would be stored with, or None if the gate would not store it."""
        return "verified"

    def withhold(self, memory: Memory, speaker: str) -> bool:
        """True if a recalled memory goes to the user as a system notice instead of to the model."""
        return False

    def notice(self, memories: list[Memory], speaker: str) -> str:
        """The system-written disclosure appended to the reply for withheld memories."""
        return ""


class AllowAllGate(Gate):
    name = "allow-all"


class UserOnlyGate(Gate):
    name = "user-only"

    def review(self, candidate: Candidate, store: MemoryStore) -> Decision:
        if candidate.source == "user":
            return Decision("accept", "stated by a user")
        return Decision("reject", f"came from tool content ({candidate.origin})")

    def background_trust(self, candidate: Candidate) -> Trust | None:
        return "verified" if candidate.source == "user" else None


def _ids(memories: list[Memory]) -> str:
    return ", ".join(f"#{m.id}" for m in memories)


class ConflictQuarantineGate(Gate):
    name = "conflict-quarantine"

    def __init__(self, detector: ConflictDetector):
        self.detector = detector

    def review(self, candidate: Candidate, store: MemoryStore) -> Decision:
        if candidate.source == "user":
            return Decision("accept", "stated by a user")
        trusted = [m for m in self.detector.find(candidate, store) if m.source == "user"]
        if trusted:
            return Decision("quarantine", f"tool content contradicts user-stated memory {_ids(trusted)}")
        return Decision("accept", "no conflict with user-stated memories")


class LastWriteWinsGate(Gate):
    name = "last-write-wins"

    def __init__(self, detector: ConflictDetector):
        self.detector = detector

    def review(self, candidate: Candidate, store: MemoryStore) -> Decision:
        conflicts = self.detector.find(candidate, store)
        if conflicts:
            return Decision("accept", f"replaces {_ids(conflicts)}", supersedes=tuple(m.id for m in conflicts))
        return Decision("accept", "no conflict")


class BoundedOccupancyGate(Gate):
    name = "bounded-occupancy"

    def __init__(self, max_untrusted: int = 1):
        self.max_untrusted = max_untrusted

    def recall(self, query: str, store: MemoryStore, k: int, speaker: str) -> list[Memory]:
        chosen, untrusted = [], 0
        for memory, _ in store.search(query, k=len(store.all())):
            if memory.source == "tool":
                if untrusted >= self.max_untrusted:
                    continue
                untrusted += 1
            chosen.append(memory)
            if len(chosen) == k:
                break
        return chosen


class ThymusGate(Gate):
    name = "thymus"

    def __init__(
        self,
        detector: ConflictDetector,
        classifier: ClaimClassifier,
        trusted_origins: tuple[str, ...] = ("calendar:",),
        *,
        screen: bool = True,
        same_origin_only: bool = True,
        disclose: bool = True,
        hide_contested: bool = False,
        require_auth: bool = False,
        contest_other_users: bool = False,
        notice: bool = False,
        soft_supersede: bool = False,
        name: str = "thymus",
    ):
        self.detector = detector
        self.classifier = classifier
        self.trusted_origins = trusted_origins  # the user's own integrations
        # Ablation switches; the defaults are the full gate.
        self.screen = screen
        self.same_origin_only = same_origin_only
        self.disclose = disclose
        self.hide_contested = hide_contested
        # Version 2 rules (thymus-v2): a source replaces its own fact only through an
        # authenticated channel; a user's claim that contradicts another user is contested;
        # contested claims reach the user as a system notice instead of the model.
        self.require_auth = require_auth
        self.contest_other_users = contest_other_users
        self.notice_mode = notice
        self.soft_supersede = soft_supersede
        self.name = name

    def _trusted_origin(self, candidate: Candidate) -> bool:
        authentic = candidate.authenticated or not self.require_auth
        return candidate.origin.startswith(self.trusted_origins) and authentic

    def _trust(self, candidate: Candidate) -> Trust:
        if candidate.source == "user" or self._trusted_origin(candidate):
            return "verified"
        return "unverified"

    def background_trust(self, candidate: Candidate) -> Trust | None:
        return self._trust(candidate)  # background facts are facts and conflict with nothing

    def review(self, candidate: Candidate, store: MemoryStore) -> Decision:
        if self.screen and candidate.source == "tool" and not self._trusted_origin(candidate):
            kind = self.classifier.kind(candidate.text)
            if kind != "fact":
                return Decision("reject", f"{candidate.origin} tried to speak for the user ({kind})")

        trust = self._trust(candidate)
        conflicts = self.detector.find(candidate, store)
        if not conflicts:
            return Decision("accept", f"new {trust} fact", trust=trust)

        if candidate.source == "user":
            # Users may correct facts from tools and their own earlier statements,
            # but not what a different user told a shared assistant.
            own = [m for m in conflicts if m.source == "tool" or m.speaker == candidate.speaker]
            contested = tuple(m.id for m in conflicts if m not in own) if self.contest_other_users else ()
            return Decision("accept", f"user update replaces {_ids(own)}", tuple(m.id for m in own), trust, contested)

        can_replace = candidate.authenticated or not self.require_auth
        same_origin = [
            m for m in conflicts if (m.origin == candidate.origin and can_replace) or not self.same_origin_only
        ]
        others = [m for m in conflicts if m not in same_origin]
        if others and self.hide_contested:
            return Decision("quarantine", f"contradicts {_ids(others)} from other sources, hidden")
        if others:
            trust = "unverified"
        reason = f"same-origin update replaces {_ids(same_origin)}" if same_origin else "no replacement"
        if others:
            reason += f"; contradicts {_ids(others)} from other sources, kept unverified"
        return Decision("accept", reason, tuple(m.id for m in same_origin), trust, tuple(m.id for m in others))

    def render(self, memory: Memory, speaker: str) -> str:
        line = super().render(memory, speaker)
        if memory.older:
            line += " [older version: later updated]"
        return disclose(line, memory, speaker) if self.disclose else line

    def withhold(self, memory: Memory, speaker: str) -> bool:
        return self.notice_mode and contested(memory, speaker)

    def notice(self, memories: list[Memory], speaker: str) -> str:
        if not memories:
            return ""
        claims = "; ".join(
            f"{'another user of this assistant' if m.source == 'user' else 'a message from ' + m.origin} said: "
            f'"{m.text}"'
            for m in sorted(memories, key=lambda m: m.created_at)
        )
        return (
            f"Note: I also have unconfirmed information that contradicts this. {claims}. "
            "I have not used it in my answer; please check with the source directly before acting on it."
        )


def contested(memory: Memory, speaker: str) -> bool:
    """A claim that contradicts another source and is not the viewer's own verified statement."""
    return bool(memory.contradicts) and (memory.trust == "unverified" or memory.speaker != speaker)


def disclose(line: str, memory: Memory, speaker: str) -> str:
    """Append the source label that unverified memories carry at recall."""
    if memory.trust == "unverified" and memory.contradicts:
        return f"{line} [unverified: from {memory.origin}; contradicts an earlier memory]"
    if memory.trust == "unverified":
        return f"{line} [unverified: from {memory.origin}]"
    if memory.source == "user" and memory.speaker != speaker:
        return f"{line} [unverified: said by another user of this assistant]"
    return line


class LabelOnlyGate(Gate):
    """Keep every memory; label untrusted ones at recall; never replace anything."""

    name = "label-only"

    def __init__(self, trusted_origins: tuple[str, ...] = ("calendar:",)):
        self.trusted_origins = trusted_origins

    def background_trust(self, candidate: Candidate) -> Trust | None:
        if candidate.source == "user" or candidate.origin.startswith(self.trusted_origins):
            return "verified"
        return "unverified"

    def review(self, candidate: Candidate, store: MemoryStore) -> Decision:
        trust = self.background_trust(candidate)
        return Decision("accept", f"stored as {trust}", trust=trust)

    def render(self, memory: Memory, speaker: str) -> str:
        return disclose(super().render(memory, speaker), memory, speaker)


GATES: dict[str, Callable[[LLM], Gate]] = {
    "allow-all": lambda llm: AllowAllGate(),
    "user-only": lambda llm: UserOnlyGate(),
    "conflict-quarantine": lambda llm: ConflictQuarantineGate(LLMConflictDetector(llm)),
    "last-write-wins": lambda llm: LastWriteWinsGate(LLMConflictDetector(llm)),
    "bounded-occupancy": lambda llm: BoundedOccupancyGate(),
    "label-only": lambda llm: LabelOnlyGate(),
    "thymus": lambda llm: ThymusGate(LLMConflictDetector(llm), LLMClaimClassifier(llm)),
    "thymus-no-screen": lambda llm: ThymusGate(
        LLMConflictDetector(llm), LLMClaimClassifier(llm), screen=False, name="thymus-no-screen"),
    "thymus-any-origin": lambda llm: ThymusGate(
        LLMConflictDetector(llm), LLMClaimClassifier(llm), same_origin_only=False, name="thymus-any-origin"),
    "thymus-no-labels": lambda llm: ThymusGate(
        LLMConflictDetector(llm), LLMClaimClassifier(llm), disclose=False, name="thymus-no-labels"),
    "thymus-hide": lambda llm: ThymusGate(
        LLMConflictDetector(llm), LLMClaimClassifier(llm), hide_contested=True, name="thymus-hide"),
    "thymus-v2": lambda llm: ThymusGate(
        LLMConflictDetector(llm), LLMClaimClassifier(llm), require_auth=True, contest_other_users=True, notice=True,
        name="thymus-v2"),
    "thymus-v2-soft": lambda llm: ThymusGate(
        LLMConflictDetector(llm), LLMClaimClassifier(llm), require_auth=True, contest_other_users=True, notice=True,
        soft_supersede=True, name="thymus-v2-soft"),
    "thymus-v2-inline": lambda llm: ThymusGate(
        LLMConflictDetector(llm), LLMClaimClassifier(llm), require_auth=True, contest_other_users=True,
        name="thymus-v2-inline"),
}

# The gates compared in the main experiment; the ablations are run separately.
MAIN_GATES = (
    "allow-all", "user-only", "conflict-quarantine", "last-write-wins", "bounded-occupancy", "label-only", "thymus",
)
ABLATIONS = ("thymus-no-screen", "thymus-any-origin", "thymus-no-labels", "thymus-hide")
# Version 2 of the gate and its inline-label variant (see ThymusGate).
VERSION_2 = ("thymus-v2", "thymus-v2-inline", "thymus-v2-soft")


def make_gate(name: str, llm: LLM) -> Gate:
    try:
        return GATES[name](llm)
    except KeyError:
        raise ValueError(f"unknown gate {name!r}; choose from {', '.join(GATES)}") from None
