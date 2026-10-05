"""Write-gates: the checks every candidate memory passes before it is stored.

Weeks 5-8 add the real thymus gates here (provenance trust, contradiction checks,
quarantine and maturation, versioning). The two below are the reference points
every new gate is measured against:

- allow-all: no defence, what most memory agents ship with.
- user-only: the naive strict defence. It blocks every attack that arrives through
  tool content, but also every legitimate fact or update that arrives that way.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from thymus.memory import Candidate, MemoryStore

Action = Literal["accept", "reject", "quarantine"]


@dataclass(frozen=True)
class Decision:
    action: Action
    reason: str


class WriteGate(Protocol):
    name: str

    def review(self, candidate: Candidate, store: MemoryStore) -> Decision: ...


class AllowAllGate:
    name = "allow-all"

    def review(self, candidate: Candidate, store: MemoryStore) -> Decision:
        return Decision("accept", "no checks")


class UserOnlyGate:
    name = "user-only"

    def review(self, candidate: Candidate, store: MemoryStore) -> Decision:
        if candidate.source == "user":
            return Decision("accept", "stated by a user")
        return Decision("reject", f"came from tool content ({candidate.origin})")


GATES: dict[str, type] = {gate.name: gate for gate in (AllowAllGate, UserOnlyGate)}


def make_gate(name: str) -> WriteGate:
    try:
        return GATES[name]()
    except KeyError:
        raise ValueError(f"unknown gate {name!r}; choose from {', '.join(GATES)}") from None
