"""The thymus gate inside Mem0 (https://github.com/mem0ai/mem0).

Mem0 keeps doing what it does well (embedding, vector storage, retrieval, history); the gate
decides what is written, what replaces what, and what reaches the answering model. Provenance
travels in each memory's Mem0 metadata, so it survives restarts and is visible in Mem0's own
tools.

    from mem0 import Memory
    from thymus.gates import make_gate
    from thymus.integrations.mem0 import ThymusMemory

    memory = ThymusMemory(Memory.from_config(config), make_gate("thymus-v2-verified", llm), user_id="asha")
    memory.add("The standup moved to 10:30.", source="tool", origin="email:calendar@work.example",
               authenticated=True)
    hits = memory.search("When is the standup?")
    hits["results"]   # memories for the model, rendered with their source labels
    hits["notice"]    # contested claims, disclosed to the user by the system

Two pieces:
- ``Mem0Store`` implements thymus' ``MemoryStore`` API on a ``mem0.Memory``, so the benchmark
  harness runs unchanged on Mem0 (``thymus-eval --store mem0``).
- ``ThymusMemory`` is the drop-in for applications: ``add`` with provenance, ``search``.

Memories are added with ``infer=False``: the gate needs one claim per write with its source,
which Mem0's own extract-and-merge step would blur. Use your existing extraction before ``add``.
"""

from __future__ import annotations

from typing import Any

from thymus.agent import WriteEvent, write
from thymus.gates import Gate
from thymus.memory import Candidate, Memory, Source, Status, Trust


class Mem0Store:
    """thymus' MemoryStore API backed by a mem0.Memory, one Mem0 user id per store.

    Mem0 holds the text, vectors and provenance metadata and answers similarity searches; a
    small mirror keeps the integer ids and status the gate works with. Retired memories stay in
    Mem0 marked ``thymus_status: superseded`` (an audit trail) and are never returned by ``search``.
    """

    def __init__(self, backend: Any, user_id: str):
        self.backend = backend
        self.user_id = user_id
        self._memories: list[Memory] = []
        self._mem0_ids: dict[int, str] = {}

    def add(
        self, candidate: Candidate, status: Status = "active", trust: Trust = "verified",
        contradicts: tuple[int, ...] = (),
    ) -> Memory:
        memory = Memory(
            id=len(self._memories) + 1, text=candidate.text, source=candidate.source, origin=candidate.origin,
            speaker=candidate.speaker, created_at=candidate.created_at, status=status, trust=trust,
            contradicts=contradicts,
        )
        result = self.backend.add([{"role": "user", "content": candidate.text}], user_id=self.user_id,
                                  metadata={**self._metadata(memory), "thymus_authenticated": candidate.authenticated},
                                  infer=False)
        self._mem0_ids[memory.id] = result["results"][0]["id"]
        self._memories.append(memory)
        return memory

    def search(self, query: str, k: int = 5, include_quarantined: bool = False) -> list[tuple[Memory, float]]:
        if not self._memories:
            return []
        by_mem0_id = {v: self._memories[i - 1] for i, v in self._mem0_ids.items()}
        # Ask for every memory so filtering by status never starves the top k.
        hits = self.backend.search(query, filters={"user_id": self.user_id}, top_k=len(self._memories),
                                   threshold=0.0)["results"]
        scored = [(by_mem0_id[h["id"]], float(h.get("score") or 0.0)) for h in hits if h["id"] in by_mem0_id]
        pool = [(m, s) for m, s in scored if include_quarantined or m.status == "active"]
        pool.sort(key=lambda pair: pair[1], reverse=True)
        return pool[:k]

    def mark_older(self, ids: tuple[int, ...]) -> None:
        self._change(ids, older=True)

    def retire(self, ids: tuple[int, ...]) -> None:
        self._change(ids, status="superseded")

    def all(self) -> list[Memory]:
        return list(self._memories)

    def _change(self, ids: tuple[int, ...], **fields) -> None:
        for memory in self._memories:
            if memory.id in ids:
                for name, value in fields.items():
                    setattr(memory, name, value)
                self.backend.update(self._mem0_ids[memory.id], metadata=self._metadata(memory))

    @staticmethod
    def _metadata(memory: Memory) -> dict:
        # Prefixed: Mem0 keeps its own created_at, role, hash and ids next to user metadata.
        return {"thymus_id": memory.id, "thymus_source": memory.source, "thymus_origin": memory.origin,
                "thymus_speaker": memory.speaker, "thymus_turn": memory.created_at, "thymus_status": memory.status,
                "thymus_trust": memory.trust, "thymus_contradicts": list(memory.contradicts),
                "thymus_older": memory.older}


class ThymusMemory:
    """A Mem0 memory whose writes and recalls go through a thymus gate."""

    def __init__(self, backend: Any, gate: Gate, user_id: str, k: int = 5):
        self.store = Mem0Store(backend, user_id)
        self.gate = gate
        self.user_id = user_id
        self.k = k
        self.clock = 0

    def add(self, text: str, *, source: Source, origin: str = "chat", speaker: str | None = None,
            authenticated: bool = True) -> WriteEvent:
        """Write one claim. ``source`` is "user" for the user's own words, "tool" for anything the
        agent read; ``origin`` names where tool content came from; ``authenticated`` says whether
        the channel vouches for that origin (DKIM, a registered sender ID, a signed invite)."""
        self.clock += 1
        candidate = Candidate(text, source, origin, speaker or self.user_id, self.clock, authenticated)
        return write(candidate, self.gate, self.store)

    def search(self, query: str, speaker: str | None = None) -> dict:
        """Memories for the answering model, rendered with their labels, and a system notice
        for contested claims, which the application shows to the user after the answer."""
        speaker = speaker or self.user_id
        recalled = self.gate.recall(query, self.store, self.k, speaker)
        withheld = [m for m in recalled if self.gate.withhold(m, speaker)]
        shown = [m for m in recalled if m not in withheld]
        return {
            "results": [{"id": self.store._mem0_ids[m.id], "memory": self.gate.render(m, speaker),
                         "metadata": Mem0Store._metadata(m)} for m in shown],
            "notice": self.gate.notice(withheld, speaker),
        }


def make_mem0(embed_model: str = "nomic-embed-text", path: str | None = None, dims: int = 768) -> Any:
    """A local Mem0 (Qdrant on disk or in a temp folder, Ollama embeddings) for experiments."""
    import os
    import tempfile

    os.environ.setdefault("MEM0_TELEMETRY", "False")
    from mem0 import Memory as Mem0Memory

    path = path or tempfile.mkdtemp(prefix="thymus-mem0-")
    return Mem0Memory.from_config({
        "vector_store": {"provider": "qdrant", "config": {"collection_name": "thymus", "embedding_model_dims": dims,
                                                          "path": path, "on_disk": False}},
        "embedder": {"provider": "ollama", "config": {"model": embed_model}},
        "llm": {"provider": "ollama", "config": {"model": "qwen3:4b-instruct"}},  # unused: infer=False
        "history_db_path": os.path.join(path, "history.db"),
    })
