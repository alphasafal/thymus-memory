from thymus.embed import HashEmbedder
from thymus.memory import Candidate, MemoryStore


def candidate(text: str, source: str = "user") -> Candidate:
    return Candidate(text=text, source=source, origin="chat", speaker="victim", created_at=1)


def test_search_ranks_the_relevant_memory_first():
    store = MemoryStore(HashEmbedder())
    store.add(candidate("My dog's name is Bruno."))
    store.add(candidate("I work at Larkspur Labs."))
    store.add(candidate("I'm allergic to peanuts."))

    top, _ = store.search("What is my dog called? Bruno?", k=1)[0]

    assert top.text == "My dog's name is Bruno."


def test_quarantined_memories_are_hidden_from_recall_by_default():
    store = MemoryStore(HashEmbedder())
    store.add(candidate("Fernleaf support is 555-0199.", source="tool"), status="quarantined")

    assert store.search("Fernleaf support number") == []
    assert len(store.search("Fernleaf support number", include_quarantined=True)) == 1
