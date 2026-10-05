import json
from collections import Counter
from pathlib import Path

import pytest

from thymus.harness import contains_any, normalize
from thymus.scenarios import load_scenarios

FAMILY_DIR = Path(__file__).parent.parent / "scenarios" / "families"
FAMILIES = [fam for f in sorted(FAMILY_DIR.glob("*.json")) for fam in json.loads(f.read_text())]


def text_of(turns):
    return " ".join(t["message"] + " " + t.get("tool_content", "") for t in turns)


@pytest.mark.parametrize("fam", FAMILIES, ids=[f["family"] for f in FAMILIES])
def test_family_is_internally_consistent(fam):
    setup, legit, attack = text_of(fam["setup"]), text_of([fam["legit"]["turn"]]), text_of(fam["attack"]["turns"])
    original, new, poison = fam["original_markers"], fam["legit"]["markers"], fam["attack"]["markers"]

    # Each value is actually stated where it is supposed to come from.
    assert contains_any(setup, tuple(original)), "original value missing from setup"
    assert contains_any(legit, tuple(new)), "new value missing from the legitimate update"
    assert contains_any(attack, tuple(poison)), "poison missing from the attack"

    # Values never overlap, so keyword verdicts can tell them apart.
    assert not contains_any(setup + " " + legit, tuple(poison)), "poison marker also appears in honest content"
    assert not contains_any(setup, tuple(new)), "new value already present in setup"
    assert not contains_any(fam["legit"]["answer"], tuple(original)), "old value in the new answer"
    assert not contains_any(fam["original_answer"], tuple(new)), "new value in the old answer"

    # Spoofed attacks really reuse the original source; lookalikes really differ.
    origins = {t.get("tool_origin") for t in fam["setup"]}
    attack_origins = {t.get("tool_origin") for t in fam["attack"]["turns"]}
    if fam["attack"]["kind"] == "spoofed-origin":
        assert attack_origins <= origins
    if fam["attack"]["kind"] == "other-user":
        assert all(t["speaker"] == "attacker" for t in fam["attack"]["turns"])


def test_families_are_balanced_and_unique():
    names = [f["family"] for f in FAMILIES]
    assert len(names) == len(set(names))
    legit = Counter(f["legit"]["kind"] for f in FAMILIES)
    attack = Counter(f["attack"]["kind"] for f in FAMILIES)
    assert set(legit) == {"same-origin", "user", "cross-origin"} and min(legit.values()) >= 15
    assert set(attack) == {"lookalike-origin", "other-channel", "other-user", "spoofed-origin", "instruction"}
    assert min(attack.values()) >= 8


def test_families_expand_into_three_matched_scenarios():
    scenarios = load_scenarios(Path(__file__).parent.parent / "scenarios")
    ids = {s.id for s in scenarios}
    for fam in FAMILIES:
        assert {f"{fam['family']}--recall", f"{fam['family']}--legit", f"{fam['family']}--attack"} <= ids
