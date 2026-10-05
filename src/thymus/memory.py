"""The agent's long-term memory store."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from thymus.embed import Embedder, Vector, cosine

Source = Literal["user", "tool"]
Status = Literal["active", "quarantined", "superseded"]


@dataclass(frozen=True)
class Candidate:
    """A memory the agent wants to write, before any gate has looked at it.

    Provenance is recorded by construction (which input segment the memory was
    extracted from), never by asking the model, so injected text cannot forge it.
    """

    text: str
    source: Source  # "user": the person typed it; "tool": content the agent read
    origin: str  # "chat", or where tool content came from, e.g. "web:bank-reviews.example"
    speaker: str  # the user the agent was talking to when the memory was formed
    created_at: int  # logical time: the agent's turn counter


@dataclass
class Memory:
    id: int
    text: str
    source: Source
    origin: str
    speaker: str
    created_at: int
    status: Status = "active"
    vector: Vector = field(default_factory=list, repr=False)


class MemoryStore:
    """Append-only store with cosine-similarity recall. Shared by every speaker,
    like the shared deployments that MINJA-style attacks target."""

    def __init__(self, embedder: Embedder):
        self.embedder = embedder
        self._memories: list[Memory] = []

    def add(self, candidate: Candidate, status: Status = "active") -> Memory:
        memory = Memory(
            id=len(self._memories) + 1,
            text=candidate.text,
            source=candidate.source,
            origin=candidate.origin,
            speaker=candidate.speaker,
            created_at=candidate.created_at,
            status=status,
            vector=self.embedder.embed([candidate.text])[0],
        )
        self._memories.append(memory)
        return memory

    def search(self, query: str, k: int = 5, include_quarantined: bool = False) -> list[tuple[Memory, float]]:
        pool = [m for m in self._memories if include_quarantined or m.status == "active"]
        if not pool:
            return []
        query_vector = self.embedder.embed([query])[0]
        scored = [(m, cosine(query_vector, m.vector)) for m in pool]
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:k]

    def retire(self, ids: tuple[int, ...]) -> None:
        """Mark memories as superseded by a newer one; they are no longer recalled."""
        for memory in self._memories:
            if memory.id in ids:
                memory.status = "superseded"

    def all(self) -> list[Memory]:
        return list(self._memories)
