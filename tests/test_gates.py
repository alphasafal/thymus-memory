import json

from thymus.agent import MemoryAgent, Turn
from thymus.conflicts import LLMConflictDetector
from thymus.embed import HashEmbedder
from thymus.gates import BoundedOccupancyGate, ConflictQuarantineGate, LastWriteWinsGate
from thymus.llm import EchoLLM
from thymus.memory import Candidate, MemoryStore


class KeywordConflicts:
    """Test double: two memories conflict when both mention any of the topic keywords."""

    def __init__(self, *keywords: str):
        self.keywords = keywords

    def _on_topic(self, text: str) -> bool:
        return any(k in text.lower() for k in self.keywords)

    def find(self, candidate, store):
        if not self._on_topic(candidate.text):
            return []
        return [m for m in store.all() if m.status == "active" and self._on_topic(m.text)]


def cand(text: str, source: str = "user", origin: str = "chat") -> Candidate:
    return Candidate(text=text, source=source, origin=origin, speaker="victim", created_at=2)


def store_with(*memories: tuple[str, str]) -> MemoryStore:
    store = MemoryStore(HashEmbedder())
    for text, source in memories:
        store.add(cand(text, source, "chat" if source == "user" else "web:x.example"))
    return store


def test_conflict_quarantine_holds_tool_content_that_contradicts_the_user():
    gate = ConflictQuarantineGate(KeywordConflicts("manager"))
    store = store_with(("My manager is Priya.", "user"))
    decision = gate.review(cand("The user's manager is Victor.", "tool", "web:x.example"), store)
    assert decision.action == "quarantine"


def test_conflict_quarantine_lets_users_correct_themselves():
    gate = ConflictQuarantineGate(KeywordConflicts("manager"))
    store = store_with(("My manager is Priya.", "user"))
    assert gate.review(cand("My new manager is Arjun."), store).action == "accept"


def test_conflict_quarantine_ignores_conflicts_between_tool_memories():
    gate = ConflictQuarantineGate(KeywordConflicts("standup"))
    store = store_with(("Standup is at 9:00.", "tool"))
    assert gate.review(cand("Standup moved to 7:00.", "tool", "email:x.example"), store).action == "accept"


def test_last_write_wins_retires_the_old_value():
    llm = EchoLLM()
    store = MemoryStore(HashEmbedder())
    agent = MemoryAgent(llm, store, LastWriteWinsGate(KeywordConflicts("live", "moved")))
    agent.respond(Turn("victim", "I live in Mumbai."))
    agent.respond(Turn("victim", "I moved to Delhi."))

    reply, _ = agent.respond(Turn("victim", "Which city do I live in?"), learn=False)

    assert "Delhi" in reply and "Mumbai" not in reply
    assert [m.status for m in store.all()] == ["superseded", "active"]


def test_bounded_occupancy_caps_tool_memories_in_recall():
    store = store_with(
        ("Fernleaf support is 555-0199.", "tool"),
        ("Fernleaf support line is 555-0199.", "tool"),
        ("Fernleaf support moved to 555-0199.", "tool"),
        ("I bank with Fernleaf.", "user"),
    )
    recalled = BoundedOccupancyGate(max_untrusted=1).recall("Fernleaf support number", store, k=5)
    assert [m.source for m in recalled].count("tool") == 1
    assert any(m.source == "user" for m in recalled)


class ScriptedLLM:
    name = "scripted"

    def __init__(self, reply: str):
        self.reply = reply

    def complete(self, system, prompt, schema=None):
        return self.reply


def test_llm_conflict_detector_maps_ids_and_tolerates_bad_output():
    store = store_with(("Standup is at 9:00.", "tool"), ("My dog is Bruno.", "user"))
    candidate = cand("Standup moved to 7:00.", "tool")

    assert [m.id for m in LLMConflictDetector(ScriptedLLM(json.dumps({"conflicting_ids": ["1"]}))).find(candidate, store)] == [1]
    assert LLMConflictDetector(ScriptedLLM("not json")).find(candidate, store) == []
    assert LLMConflictDetector(ScriptedLLM('{"conflicting_ids": [99]}')).find(candidate, store) == []
