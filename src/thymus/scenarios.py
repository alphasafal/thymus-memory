"""Scenario files: scripted conversations followed by a probe question.

Three categories, so every gate is scored on both sides of the trade-off:

- attack: someone tries to plant a memory. Passes if the payload never reaches the probe reply.
- update: a fact changes legitimately. Passes if the probe reply has the new value.
- benign: a plain fact to remember. Passes if the probe reply has it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from thymus.agent import Turn

Category = Literal["attack", "update", "benign"]
CATEGORIES: tuple[Category, ...] = ("attack", "update", "benign")


@dataclass(frozen=True)
class Scenario:
    id: str
    category: Category
    kind: str  # finer label, e.g. "indirect-web", "minja-query", "tool-update"
    description: str
    turns: tuple[Turn, ...]
    probe: Turn
    expect_any: tuple[str, ...] = ()  # update/benign: any of these in the reply means pass
    poison_markers: tuple[str, ...] = ()  # attack: any of these in the reply means the attack worked
    stale_markers: tuple[str, ...] = ()  # update: the old value; tracked, not part of pass/fail


def _turn(data: dict) -> Turn:
    return Turn(
        speaker=data["speaker"],
        message=data["message"],
        tool_content=data.get("tool_content"),
        tool_origin=data.get("tool_origin"),
    )


def parse_scenario(data: dict) -> Scenario:
    scenario = Scenario(
        id=data["id"],
        category=data["category"],
        kind=data["kind"],
        description=data["description"],
        turns=tuple(_turn(t) for t in data["turns"]),
        probe=_turn(data["probe"]),
        expect_any=tuple(data.get("expect_any", ())),
        poison_markers=tuple(data.get("poison_markers", ())),
        stale_markers=tuple(data.get("stale_markers", ())),
    )
    if scenario.category not in CATEGORIES:
        raise ValueError(f"{scenario.id}: unknown category {scenario.category!r}")
    if scenario.category == "attack" and not scenario.poison_markers:
        raise ValueError(f"{scenario.id}: attack scenarios need poison_markers")
    if scenario.category != "attack" and not scenario.expect_any:
        raise ValueError(f"{scenario.id}: {scenario.category} scenarios need expect_any")
    return scenario


def load_scenarios(path: Path) -> list[Scenario]:
    files = sorted(path.glob("*.json")) if path.is_dir() else [path]
    scenarios = []
    for file in files:
        data = json.loads(file.read_text())
        for item in data if isinstance(data, list) else [data]:
            scenarios.append(parse_scenario(item))
    ids = [s.id for s in scenarios]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise ValueError(f"duplicate scenario ids: {', '.join(sorted(duplicates))}")
    return scenarios
