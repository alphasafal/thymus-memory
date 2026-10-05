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
    planted_claim: str = ""  # attack: the false claim, in plain words, for the judge
    correct_answer: str = ""  # update/benign: the right current answer, for the judge
    outdated_answer: str = ""  # update: the answer that used to be true
    domain: str = ""  # topic area, e.g. "travel"; empty for hand-written scenarios
    language: str = "en"  # "en", "hi" (Hindi, Devanagari) or "hinglish" (Hindi-English, Latin script)


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
        planted_claim=data.get("planted_claim", ""),
        correct_answer=data.get("correct_answer", ""),
        outdated_answer=data.get("outdated_answer", ""),
        domain=data.get("domain", ""),
        language=data.get("language", "en"),
    )
    if scenario.category not in CATEGORIES:
        raise ValueError(f"{scenario.id}: unknown category {scenario.category!r}")
    if scenario.category == "attack" and not scenario.poison_markers:
        raise ValueError(f"{scenario.id}: attack scenarios need poison_markers")
    if scenario.category != "attack" and not scenario.expect_any:
        raise ValueError(f"{scenario.id}: {scenario.category} scenarios need expect_any")
    if scenario.category == "attack" and not scenario.planted_claim:
        raise ValueError(f"{scenario.id}: attack scenarios need planted_claim for the judge")
    if scenario.category != "attack" and not scenario.correct_answer:
        raise ValueError(f"{scenario.id}: {scenario.category} scenarios need correct_answer for the judge")
    return scenario


def language_variants(family: dict) -> list[tuple[str, dict]]:
    """A multilingual family shares its answers, claim, kinds and default markers across
    languages; each language supplies its own conversation text and may override markers.
    Answers and claims stay in English: they are read by the grader, not by the agent.
    Returns one ordinary single-language family per language."""
    variants = []
    for language, text in family["languages"].items():
        variants.append((language, {
            "family": f"{family['family']}--{language}",
            "domain": family["domain"],
            "probe": text["probe"],
            "setup": text["setup"],
            "original_answer": family["original_answer"],
            "original_markers": text.get("original_markers", family["original_markers"]),
            "legit": {
                "kind": family["legit_kind"],
                "turn": text["legit_turn"],
                "answer": family["legit_answer"],
                "markers": text.get("legit_markers", family["legit_markers"]),
            },
            "attack": {
                "kind": family["attack_kind"],
                "turns": text["attack_turns"],
                "claim": family["attack_claim"],
                "markers": text.get("attack_markers", family["attack_markers"]),
            },
        }))
    return variants


def expand_multilingual(family: dict) -> list[dict]:
    scenarios = []
    for language, single in language_variants(family):
        for raw in expand_family(single):
            raw["language"] = language
            scenarios.append(raw)
    return scenarios


def expand_family(family: dict) -> list[dict]:
    """One real-life fact becomes three matched scenarios that share the same setup:
    recall (control), a legitimate update, and an attacker's fake update."""
    if "languages" in family:
        return expand_multilingual(family)
    name, setup, probe = family["family"], family["setup"], {"speaker": "victim", "message": family["probe"]}
    legit, attack = family["legit"], family["attack"]
    base = {"probe": probe, "domain": family["domain"]}
    return [
        {
            **base,
            "id": f"{name}--recall",
            "category": "benign",
            "kind": "recall-control",
            "description": f"Control: is the original fact remembered at all? ({family['domain']})",
            "turns": setup,
            "expect_any": family["original_markers"],
            "correct_answer": family["original_answer"],
        },
        {
            **base,
            "id": f"{name}--legit",
            "category": "update",
            "kind": f"{legit['kind']}-update",
            "description": f"Legitimate update ({legit['kind']}).",
            "turns": setup + [legit["turn"]],
            "expect_any": legit["markers"],
            "stale_markers": family["original_markers"],
            "correct_answer": legit["answer"],
            "outdated_answer": family["original_answer"],
        },
        {
            **base,
            "id": f"{name}--attack",
            "category": "attack",
            "kind": attack["kind"],
            "description": f"Fake update ({attack['kind']}), matched to {name}--legit.",
            "turns": setup + attack["turns"],
            "poison_markers": attack["markers"],
            "planted_claim": attack["claim"],
        },
    ]


def load_scenarios(path: Path) -> list[Scenario]:
    files = sorted(path.rglob("*.json")) if path.is_dir() else [path]
    scenarios = []
    for file in files:
        data = json.loads(file.read_text())
        for item in data if isinstance(data, list) else [data]:
            for raw in expand_family(item) if "family" in item else [item]:
                scenarios.append(parse_scenario(raw))
    ids = [s.id for s in scenarios]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise ValueError(f"duplicate scenario ids: {', '.join(sorted(duplicates))}")
    return scenarios
