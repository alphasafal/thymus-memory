"""Detecting when a new memory contradicts memories already stored."""

from __future__ import annotations

import json
from typing import Protocol

from thymus.llm import LLM
from thymus.memory import Candidate, Memory, MemoryStore, holds_several_claims

CONFLICT_SYSTEM = """You check a personal assistant's memory for contradictions.
You get a NEW memory and a list of EXISTING memories, each with an id.
An existing memory conflicts with the new one when both are about the same fact but give
different values: a different city, time, date, name, number, status or choice.
Memories about different facts do not conflict, even if they share a topic.
Return the ids of the conflicting existing memories, or an empty list."""

# Stricter variant: in a large store, similar facts about different things (a car service and
# a water-purifier service) are the main source of false conflicts.
CONFLICT_SYSTEM_SAME_SUBJECT = CONFLICT_SYSTEM + """
Two memories conflict only if they are about the SAME specific thing: the same appointment,
order, account, bill, person, trip or item. Facts of the same kind about different things
never conflict (a car service and a water-purifier service; one bank's helpline and another
bank's; two different flights). When unsure whether it is the same thing, it does not conflict."""

CONFLICT_SCHEMA = {
    "type": "object",
    "properties": {"conflicting_ids": {"type": "array", "items": {"type": "integer"}}},
    "required": ["conflicting_ids"],
    "additionalProperties": False,
}


# Second check for each claimed conflict, one pair at a time: small models confuse similar
# facts about different things far less often when they see only the two facts.
# The model first names what each fact is about without its details. Asked directly, small
# models read a changed detail as a different thing ("the meeting moved to Sept 13" is "not
# the same meeting" as the Sept 11 one), which drops exactly the conflicts that matter.
VERIFY_SYSTEM = """You compare two facts from a personal assistant's memory: A (older) and B (newer).
thing_a, thing_b: name the specific thing each fact is about in a few words, leaving out its
details (time, date, place, number, status). "The meeting with Ben moved to Friday 4 pm in
room 3" is about "meeting with Ben". If B does not say which thing it is about ("the meeting
has been moved", "it is now at 5 pm"), it is about A's thing whenever that fits.
same_thing: are thing_a and thing_b the same specific thing (the same appointment, meeting,
order, account, bill, person, trip or item)? A meeting moved to another day or room is still
the same meeting. Things of the same kind that are clearly different are not the same thing
(a car service and a water-purifier service; two banks' helplines; two different flights).
different_values: do A and B give different values for some detail of it (time, date, place,
number, name, status), so both cannot be true now?"""
VERIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "thing_a": {"type": "string"},
        "thing_b": {"type": "string"},
        "same_thing": {"type": "boolean"},
        "different_values": {"type": "boolean"},
    },
    "required": ["thing_a", "thing_b", "same_thing", "different_values"],
    "additionalProperties": False,
}

# Candidate third wording (see scripts/verifier_check.py): small models also call two facts
# different things when only one names a provider or brand.
VERIFY_SYSTEM_NAMED = VERIFY_SYSTEM + """
A name, brand or provider that appears in only one of the facts does not make them different
things: "the yoga class" and "the FitLife yoga class" can be the same class. Answer same_thing
false only when the facts show two different things."""

# The first wording, kept to reproduce the runs made with it (see docs/results-log.md).
VERIFY_SYSTEM_FIRST = """You compare two facts from a personal assistant's memory.
same_thing: are both about the SAME specific thing (the same appointment, order, account, bill,
person, trip or item)? Facts of the same kind about different things are not the same thing.
different_values: if so, do they give different values for it (time, date, place, number,
name, status), so both cannot be true now?"""
VERIFY_SCHEMA_FIRST = {
    "type": "object",
    "properties": {"same_thing": {"type": "boolean"}, "different_values": {"type": "boolean"}},
    "required": ["same_thing", "different_values"],
    "additionalProperties": False,
}


class ConflictDetector(Protocol):
    def find(self, candidate: Candidate, store: MemoryStore) -> list[Memory]: ...


class LLMConflictDetector:
    """Asks the model which of the k most similar active memories the candidate contradicts."""

    def __init__(self, llm: LLM, k: int = 5, same_subject: bool = False, verify: bool = False):
        self.llm = llm
        self.k = k
        self.system = CONFLICT_SYSTEM_SAME_SUBJECT if same_subject else CONFLICT_SYSTEM
        self.verify = verify

    def find(self, candidate: Candidate, store: MemoryStore) -> list[Memory]:
        # Only memories from earlier turns can be updated by this one: facts that arrive
        # together (one email, one message) never replace each other.
        neighbours = [
            memory for memory, _ in store.search(candidate.text, k=self.k + 5)
            if memory.created_at < candidate.created_at
        ][: self.k]
        if not neighbours:
            return []
        existing = "\n".join(f"[id {m.id}] {m.text}" for m in neighbours)
        prompt = f"<new>\n{candidate.text}\n</new>\n\n<existing>\n{existing}\n</existing>"
        raw = self.llm.complete(self.system, prompt, schema=CONFLICT_SCHEMA)
        try:
            values = json.loads(raw).get("conflicting_ids", [])
        except (json.JSONDecodeError, AttributeError):
            return []
        ids = {int(v) for v in values if isinstance(v, int) or (isinstance(v, str) and v.isdigit())}
        found = [m for m in neighbours if m.id in ids]
        if not self.verify:
            return found
        # Only single claims are compared pairwise: a memory holding a whole chat round is about
        # many things at once, so "is it the same thing?" has no answer and the first verdict stands.
        return [m for m in found if holds_several_claims(m.text) or holds_several_claims(candidate.text)
                or self._confirmed(candidate.text, m.text)]

    def _confirmed(self, new: str, old: str) -> bool:
        raw = self.llm.complete(VERIFY_SYSTEM, f"<a>\n{old}\n</a>\n\n<b>\n{new}\n</b>", schema=VERIFY_SCHEMA)
        try:
            answer = json.loads(raw)
            return bool(answer.get("same_thing")) and bool(answer.get("different_values"))
        except (json.JSONDecodeError, AttributeError):
            return True  # an unreadable answer keeps the first check's verdict
