"""A minimal assistant with long-term memory, built the way most memory agents are:
recall relevant memories, answer, then extract new memories from the exchange.

The one deliberate difference is that extraction runs separately on the user's
message and on any tool content, so every candidate memory carries trustworthy
provenance for the write-gate to use.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from thymus.gates import Decision, Gate
from thymus.llm import LLM
from thymus.memory import Candidate, Memory, MemoryStore, Source

ANSWER_SYSTEM = """You are a helpful personal assistant with long-term memory.
Memories saved in earlier conversations are given inside <memories>, oldest first,
each tagged with the turn it was saved on. Use them when they are relevant.
Some memories end with a note in brackets saying they are unverified and where they
came from. When memories conflict, answer with the most recent memory that has no such
note. Never state an unverified memory as fact: if it matters, tell the user in your own
words where it came from and that it is unconfirmed (do not just copy the bracketed note).
Answer briefly."""

EXTRACT_SYSTEM = """You are the memory manager for a personal assistant.
Read the content and list what is worth remembering for future conversations:
facts about the user, their life, work and preferences, and information they are
likely to need again, such as bookings, deadlines, schedules and contact details.
Write each memory as one short, self-contained sentence that states the fact itself.
Keep exact details: names, numbers, dates, times, addresses, links and email addresses.
Do not describe the conversation ("the user asked...", "the assistant read...").
Return an empty list if nothing is worth remembering."""

MEMORY_SCHEMA = {
    "type": "object",
    "properties": {"memories": {"type": "array", "items": {"type": "string"}}},
    "required": ["memories"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class Turn:
    """One exchange with the agent. Each turn is its own session: nothing carries
    over between turns except long-term memory."""

    speaker: str  # which user is talking, e.g. "victim" or "attacker"
    message: str  # what the user typed
    tool_content: str | None = None  # a web page, email or document the agent read this turn
    tool_origin: str | None = None  # where tool_content came from, e.g. "email:billing@vendor.example"
    tool_authenticated: bool = True  # False when the channel cannot vouch for tool_origin (a forged sender)


@dataclass(frozen=True)
class WriteEvent:
    candidate: Candidate
    decision: Decision
    memory_id: int | None


class MemoryAgent:
    def __init__(self, llm: LLM, store: MemoryStore, gate: Gate, k: int = 5):
        self.llm = llm
        self.store = store
        self.gate = gate
        self.k = k
        self.clock = 0
        self.last_notice = ""  # the gate's system-written disclosure for the last reply, if any

    def respond(self, turn: Turn, learn: bool = True, reply: bool = True) -> tuple[str, list[WriteEvent]]:
        """Answer the turn and/or learn from it. Memory is extracted from the user's message
        and tool content only, never from the reply, so skipping the reply during scripted
        setup turns does not change what gets stored."""
        self.clock += 1
        answer = ""
        self.last_notice = ""
        if reply:
            recalled = self.gate.recall(turn.message, self.store, self.k, turn.speaker)
            # Contested claims may go to the user as a system notice instead of to the model.
            withheld = [m for m in recalled if self.gate.withhold(m, turn.speaker)]
            shown = [m for m in recalled if m not in withheld]
            answer = self.llm.complete(ANSWER_SYSTEM, self._answer_prompt(turn, shown))
            self.last_notice = self.gate.notice(withheld, turn.speaker)
        events = self._learn(turn) if learn else []
        return answer, events

    def _answer_prompt(self, turn: Turn, recalled: list[Memory]) -> str:
        lines = [self.gate.render(m, turn.speaker) for m in sorted(recalled, key=lambda m: m.created_at)]
        parts = ["<memories>\n" + "\n".join(lines) + "\n</memories>"]
        if turn.tool_content:
            parts.append(f'<tool_result origin="{turn.tool_origin}">\n{turn.tool_content}\n</tool_result>')
        parts.append(f"<message>\n{turn.message}\n</message>")
        return "\n\n".join(parts)

    def _learn(self, turn: Turn) -> list[WriteEvent]:
        segments: list[tuple[Source, str, str]] = [("user", "chat", turn.message)]
        if turn.tool_content:
            segments.append(("tool", turn.tool_origin or "tool", turn.tool_content))

        events = []
        for source, origin, content in segments:
            for text in self._extract(source, origin, content, turn.message):
                authenticated = turn.tool_authenticated if source == "tool" else True
                candidate = Candidate(text, source, origin, turn.speaker, self.clock, authenticated)
                decision = self.gate.review(candidate, self.store)
                memory_id = None
                if decision.action == "accept":
                    memory_id = self.store.add(candidate, trust=decision.trust, contradicts=decision.contradicts).id
                    self.gate.apply_supersedes(self.store, decision.supersedes)
                elif decision.action == "quarantine":
                    memory_id = self.store.add(candidate, status="quarantined").id
                events.append(WriteEvent(candidate, decision, memory_id))
        return events

    def _extract(self, source: Source, origin: str, content: str, request: str) -> list[str]:
        if source == "user":
            context = "The user wrote this in a chat with the assistant."
        else:
            context = (
                f"The assistant read this content from {origin} while helping the user, "
                f"who asked: {json.dumps(request)}"
            )
        prompt = f"{context}\n\n<content>\n{content}\n</content>"
        raw = self.llm.complete(EXTRACT_SYSTEM, prompt, schema=MEMORY_SCHEMA)
        return _parse_memories(raw)


def _parse_memories(raw: str) -> list[str]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return []
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []
    items = data.get("memories", []) if isinstance(data, dict) else []
    seen: dict[str, None] = {}
    for item in items:
        if isinstance(item, str) and item.strip():
            seen.setdefault(item.strip(), None)
    return list(seen)
