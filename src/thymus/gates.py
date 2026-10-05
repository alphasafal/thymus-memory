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

And the gate this project is about:

- thymus: self/non-self screening. Tool content may add facts but never speak for the
  user; a fact can only be replaced by the user or by the source that stated it; every
  other conflicting or unvetted claim is kept but recalled with an "unverified" label.
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


class Gate:
    name = "base"

    def review(self, candidate: Candidate, store: MemoryStore) -> Decision:
        return Decision("accept", "no checks")

    def recall(self, query: str, store: MemoryStore, k: int, speaker: str) -> list[Memory]:
        return [memory for memory, _ in store.search(query, k=k)]

    def render(self, memory: Memory, speaker: str) -> str:
        """How a recalled memory appears in the model's context."""
        return f"[turn {memory.created_at}] {memory.text}"


class AllowAllGate(Gate):
    name = "allow-all"


class UserOnlyGate(Gate):
    name = "user-only"

    def review(self, candidate: Candidate, store: MemoryStore) -> Decision:
        if candidate.source == "user":
            return Decision("accept", "stated by a user")
        return Decision("reject", f"came from tool content ({candidate.origin})")


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
    ):
        self.detector = detector
        self.classifier = classifier
        self.trusted_origins = trusted_origins  # the user's own integrations

    def _trust(self, candidate: Candidate) -> Trust:
        if candidate.source == "user" or candidate.origin.startswith(self.trusted_origins):
            return "verified"
        return "unverified"

    def review(self, candidate: Candidate, store: MemoryStore) -> Decision:
        if candidate.source == "tool":
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
            return Decision("accept", f"user update replaces {_ids(own)}", tuple(m.id for m in own), trust)

        same_origin = [m for m in conflicts if m.origin == candidate.origin]
        others = [m for m in conflicts if m.origin != candidate.origin]
        if others:
            trust = "unverified"
        reason = f"same-origin update replaces {_ids(same_origin)}" if same_origin else "no replacement"
        if others:
            reason += f"; contradicts {_ids(others)} from other sources, kept unverified"
        return Decision("accept", reason, tuple(m.id for m in same_origin), trust)

    def render(self, memory: Memory, speaker: str) -> str:
        line = super().render(memory, speaker)
        if memory.trust == "unverified":
            return f"{line} [unverified: from {memory.origin}]"
        if memory.source == "user" and memory.speaker != speaker:
            return f"{line} [unverified: said by another user of this assistant]"
        return line


GATES: dict[str, Callable[[LLM], Gate]] = {
    "allow-all": lambda llm: AllowAllGate(),
    "user-only": lambda llm: UserOnlyGate(),
    "conflict-quarantine": lambda llm: ConflictQuarantineGate(LLMConflictDetector(llm)),
    "last-write-wins": lambda llm: LastWriteWinsGate(LLMConflictDetector(llm)),
    "bounded-occupancy": lambda llm: BoundedOccupancyGate(),
    "thymus": lambda llm: ThymusGate(LLMConflictDetector(llm), LLMClaimClassifier(llm)),
}


def make_gate(name: str, llm: LLM) -> Gate:
    try:
        return GATES[name](llm)
    except KeyError:
        raise ValueError(f"unknown gate {name!r}; choose from {', '.join(GATES)}") from None
