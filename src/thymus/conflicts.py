"""Detecting when a new memory contradicts memories already stored."""

from __future__ import annotations

import json
from typing import Protocol

from thymus.llm import LLM
from thymus.memory import Candidate, Memory, MemoryStore

CONFLICT_SYSTEM = """You check a personal assistant's memory for contradictions.
You get a NEW memory and a list of EXISTING memories, each with an id.
An existing memory conflicts with the new one when both are about the same fact but give
different values: a different city, time, date, name, number, status or choice.
Memories about different facts do not conflict, even if they share a topic.
Return the ids of the conflicting existing memories, or an empty list."""

CONFLICT_SCHEMA = {
    "type": "object",
    "properties": {"conflicting_ids": {"type": "array", "items": {"type": "integer"}}},
    "required": ["conflicting_ids"],
    "additionalProperties": False,
}


class ConflictDetector(Protocol):
    def find(self, candidate: Candidate, store: MemoryStore) -> list[Memory]: ...


class LLMConflictDetector:
    """Asks the model which of the k most similar active memories the candidate contradicts."""

    def __init__(self, llm: LLM, k: int = 5):
        self.llm = llm
        self.k = k

    def find(self, candidate: Candidate, store: MemoryStore) -> list[Memory]:
        neighbours = [memory for memory, _ in store.search(candidate.text, k=self.k)]
        if not neighbours:
            return []
        existing = "\n".join(f"[id {m.id}] {m.text}" for m in neighbours)
        prompt = f"<new>\n{candidate.text}\n</new>\n\n<existing>\n{existing}\n</existing>"
        raw = self.llm.complete(CONFLICT_SYSTEM, prompt, schema=CONFLICT_SCHEMA)
        try:
            values = json.loads(raw).get("conflicting_ids", [])
        except (json.JSONDecodeError, AttributeError):
            return []
        ids = {int(v) for v in values if isinstance(v, int) or (isinstance(v, str) and v.isdigit())}
        return [m for m in neighbours if m.id in ids]
