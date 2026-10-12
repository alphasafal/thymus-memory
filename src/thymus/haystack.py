"""Background memories for long-memory runs (`thymus-eval --haystack N`).

Real assistants hold many memories, and an attack or an update has to win recall against
all of them. A haystack run fills the store with N facts from *other* families before a
scenario starts. Each background fact keeps the provenance it has in its own family (the
user said it in chat, or it came from that family's email, SMS or web origin).

Each background memory is another family's original message (the calendar entry, the email,
what the user said), so it names its own subject, as a stored memory would: an extracted
sentence such as "The EMI is 14,200" is ambiguous on its own and would make false conflicts
the benchmark's fault. Families about the same thing (eval/haystack_related.json, and every
X / X-india pair) never supply each other's background, so background facts never conflict
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


RELATED = Path(__file__).resolve().parents[2] / "eval" / "haystack_related.json"


def background_pool(scenario_dir: Path) -> list[BackgroundFact]:
    """One memory per family: the English setup message, with the provenance of its setup."""
    pool = []
    for path in sorted((scenario_dir / "families").rglob("*.json")):
        for fam in json.loads(path.read_text()):
            setup = (fam["languages"]["en"] if "languages" in fam else fam)["setup"]
            turn = setup[-1]
            origin = turn.get("tool_origin")
            text = turn.get("tool_content") or turn["message"]
            pool.append(BackgroundFact(fam["family"], text, "tool" if origin else "user", origin or "chat"))
    return pool


def scenario_family(scenario_id: str) -> str:
    return scenario_id.split("--")[0]


def _subject(name: str, groups: dict[str, int]) -> str | int:
    base = name.removesuffix("-india")
    return groups.get(name, groups.get(base, base))


def related_groups(path: Path = RELATED) -> dict[str, int]:
    if not path.exists():
        return {}
    return {name: n for n, group in enumerate(json.loads(path.read_text())["groups"]) for name in group}


def fill(store: MemoryStore, gate: Gate, scenario_id: str, pool: list[BackgroundFact], n: int, seed: int = 0) -> int:
    """Add n background facts the gate would have admitted; returns how many were stored."""
    groups = related_groups()
    own = _subject(scenario_family(scenario_id), groups)
    others = [fact for fact in pool if _subject(fact.family, groups) != own]
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
