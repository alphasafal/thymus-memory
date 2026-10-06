"""Background memories for long-memory runs (`thymus-eval --haystack N`).

Real assistants hold many memories, and an attack or an update has to win recall against
all of them. A haystack run fills the store with N facts from *other* families before a
scenario starts. Each background fact keeps the provenance it has in its own family (the
user said it in chat, or it came from that family's email, SMS or web origin).

Background facts come from different families, so they never conflict with each other or
with the scenario. That means every gate's decision for them is known without model calls:
see ``Gate.background_trust``. The same scenario family always gets the same background
facts, for every gate and language, so comparisons stay paired.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

from thymus.gates import Gate
from thymus.memory import Candidate, MemoryStore


@dataclass(frozen=True)
class BackgroundFact:
    family: str
    text: str
    source: str
    origin: str


def background_pool(scenario_dir: Path) -> list[BackgroundFact]:
    """One fact per family: the family's original value, with the provenance of its setup."""
    pool = []
    for path in sorted((scenario_dir / "families").rglob("*.json")):
        for fam in json.loads(path.read_text()):
            setup = (fam["languages"]["en"] if "languages" in fam else fam)["setup"]
            origin = next((t["tool_origin"] for t in reversed(setup) if t.get("tool_origin")), None)
            source = "tool" if origin else "user"
            pool.append(BackgroundFact(fam["family"], fam["original_answer"], source, origin or "chat"))
    return pool


def scenario_family(scenario_id: str) -> str:
    return scenario_id.split("--")[0]


def fill(store: MemoryStore, gate: Gate, scenario_id: str, pool: list[BackgroundFact], n: int, seed: int = 0) -> int:
    """Add n background facts the gate would have admitted; returns how many were stored."""
    own = scenario_family(scenario_id)
    others = [fact for fact in pool if fact.family != own]
    if n > len(others):
        raise ValueError(f"--haystack {n} is larger than the {len(others)} background facts available")
    chosen = random.Random(f"{seed}:{own}").sample(others, n)
    stored = 0
    for fact in chosen:
        candidate = Candidate(fact.text, fact.source, fact.origin, "victim", created_at=0)
        trust = gate.background_trust(candidate)
        if trust is not None:
            store.add(candidate, trust=trust)
            stored += 1
    return stored
