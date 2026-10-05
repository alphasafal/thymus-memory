from pathlib import Path

import pytest

from thymus.agent import _parse_memories
from thymus.embed import HashEmbedder
from thymus.gates import AllowAllGate, UserOnlyGate
from thymus.harness import contains_any, run_scenario, summarize
from thymus.llm import EchoLLM
from thymus.scenarios import load_scenarios

SCENARIOS = {s.id: s for s in load_scenarios(Path(__file__).parent.parent / "scenarios")}


def run(scenario_id: str, gate):
    return run_scenario(SCENARIOS[scenario_id], EchoLLM(), HashEmbedder(), gate)


def test_every_category_has_scenarios():
    categories = {s.category for s in SCENARIOS.values()}
    assert categories == {"attack", "update", "benign"}


def test_markers_ignore_case_and_punctuation():
    assert contains_any("Call +1 555 0199 today", ("555-0199",))
    assert not contains_any("Call 555-0100", ("555-0199",))


def test_allow_all_lets_a_web_injection_through():
    result = run("web-fake-support-number", AllowAllGate())
    assert result.poison_stored and result.poison_used and result.passed is False


def test_user_only_blocks_a_web_injection():
    result = run("web-fake-support-number", UserOnlyGate())
    assert result.poison_stored is False and result.passed is True
    assert any(w["action"] == "reject" and w["source"] == "tool" for w in result.writes)


def test_user_only_does_not_stop_query_only_injection():
    # The attacker is a user of the shared assistant, so source alone can't catch it.
    result = run("minja-refund-policy", UserOnlyGate())
    assert result.poison_used is True


def test_user_only_also_blocks_legitimate_tool_facts():
    # The cost side of the trade-off.
    assert run("email-flight-booking", AllowAllGate()).passed is True
    assert run("email-flight-booking", UserOnlyGate()).passed is False


def test_user_update_is_recalled():
    result = run("user-moved-city", AllowAllGate())
    assert result.passed is True


def test_summary_reports_both_sides_of_the_trade_off():
    results = [run(sid, gate) for gate in (AllowAllGate(), UserOnlyGate()) for sid in SCENARIOS]
    summary = summarize(results)
    assert summary["allow-all"]["attack_success_rate"] > summary["user-only"]["attack_success_rate"]
    assert summary["allow-all"]["benign_accuracy"] > summary["user-only"]["benign_accuracy"]
    assert summary["allow-all"]["errors"] == 0


@pytest.mark.parametrize(
    "raw, expected",
    [
        ('{"memories": ["a", "b", "a"]}', ["a", "b"]),
        ('Sure! {"memories": ["x"]}', ["x"]),
        ("not json", []),
        ('{"memories": [1, "  ", "ok"]}', ["ok"]),
    ],
)
def test_parse_memories_is_forgiving(raw, expected):
    assert _parse_memories(raw) == expected


def test_markers_work_in_hindi():
    assert contains_any("आपका बिल ₹1,960 है", ("1,960",))
    assert contains_any("आपकी डिलीवरी 16 अक्टूबर को होगी", ("16 अक्टूबर",))
    assert not contains_any("आपकी डिलीवरी 16 अक्टूबर को होगी", ("6 अक्टूबर",))
