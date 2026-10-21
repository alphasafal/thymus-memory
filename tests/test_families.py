import re
import json
from collections import Counter
from pathlib import Path

import pytest

from thymus.harness import contains_any
from thymus.scenarios import language_variants, load_scenarios

FAMILY_DIR = Path(__file__).parent.parent / "scenarios" / "families"
FAMILIES = [fam for f in sorted(FAMILY_DIR.glob("*.json")) for fam in json.loads(f.read_text())]
INDIA = [fam for f in sorted((FAMILY_DIR / "india").glob("*.json")) for fam in json.loads(f.read_text())]
INDIA_VARIANTS = [single for fam in INDIA for _, single in language_variants(fam)]


def text_of(turns):
    return " ".join(t["message"] + " " + t.get("tool_content", "") for t in turns)


@pytest.mark.parametrize("fam", FAMILIES + INDIA_VARIANTS, ids=[f["family"] for f in FAMILIES + INDIA_VARIANTS])
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


def test_india_families_have_all_three_languages():
    assert INDIA, "no India families found"
    for fam in INDIA:
        assert set(fam["languages"]) == {"en", "hi", "hinglish"}, fam["family"]
        hindi = " ".join(t["message"] + t.get("tool_content", "") for t in fam["languages"]["hi"]["setup"])
        assert any("\u0900" <= ch <= "\u097f" for ch in hindi), f"{fam['family']}: Hindi text is not in Devanagari"


SCENARIO_DIR = Path(__file__).parent.parent / "scenarios"
ALL_TEXT = "\n".join(f.read_text() for d in (SCENARIO_DIR, SCENARIO_DIR.parent / "scenarios-real", SCENARIO_DIR.parent / "scenarios-gate-aware", SCENARIO_DIR.parent / "scenarios-fresh") for f in sorted(d.rglob("*.json")))


def test_no_phone_number_could_belong_to_a_real_person_or_company():
    # Indian mobiles are 10 digits starting 6-9; 1800 numbers are real toll-free lines.
    # Benchmark numbers use the unallocated +91-555xx range or the US 555-01xx fiction range.
    digits = [re.sub(r"\D", "", n) for n in re.findall(r"\+?\d[\d -]{7,}\d", ALL_TEXT)]
    risky = [d for d in digits if re.fullmatch(r"(91)?[6-9]\d{9}", d) or d.startswith("1800")]
    assert not risky, f"real-looking phone numbers: {sorted(set(risky))}"


# Made-up UPI handles: real ones (okaxis, oksbi, ybl, paytm, upi…) must never appear.
FICTIONAL_UPI_HANDLES = {"okbank", "upi-pay", "upi-fast", "upi-renew", "upi-quick"}


def test_every_domain_and_upi_handle_is_made_up():
    text = ALL_TEXT.lower()
    real_tlds = re.findall(r"\b[\w-]+(?:\.[\w-]+)*\.(?:com|in|org|net|co|io|app|gov|bank|info|xyz|me|ai)\b", text)
    assert not real_tlds, f"real-looking domains: {sorted(set(real_tlds))[:20]}"
    for handle in re.findall(r"[\w.-]+@([a-z][\w-]*(?:\.[\w-]+)*)", text):  # handles start with a letter
        if "." in handle:
            assert handle.endswith((".example", ".test", ".invalid")), f"email domain {handle} is not reserved"
        else:
            assert handle in FICTIONAL_UPI_HANDLES, f"UPI handle @{handle} is not on the made-up list"
    for origin in re.findall(r"\b(?:web|email|doc):([\w.@/-]+)", text):
        domain = origin.split("@")[-1].split("/")[0].rstrip(".")
        if domain.count(".") and not domain.endswith((".pdf", ".docx")):
            assert domain.endswith((".example", ".test", ".invalid")), f"origin {origin} is not a reserved domain"
