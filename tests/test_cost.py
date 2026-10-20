from pathlib import Path

from thymus.claims import CLAIM_SYSTEM
from thymus.conflicts import CONFLICT_SYSTEM, VERIFY_SYSTEM
from thymus.cost import CountingLLM, Usage, gate_overhead
from thymus.embed import HashEmbedder
from thymus.gates import make_gate
from thymus.harness import run_scenario
from thymus.llm import EchoLLM
from thymus.report import confirmation_burden, cost_table, held_for_confirmation
from thymus.scenarios import load_scenarios

SCENARIOS = {s.id: s for s in load_scenarios(Path(__file__).parent.parent / "scenarios")}


class Fixed:
    name = "fixed"

    def complete(self, system, prompt, schema=None):
        return "x" * 40


def test_counting_llm_sorts_calls_by_job_and_reports_differences():
    usage = Usage()
    llm = CountingLLM(Fixed(), usage)
    llm.complete(CLAIM_SYSTEM, "a" * 400)
    before = usage.snapshot()
    llm.complete(CONFLICT_SYSTEM, "b" * 400)
    llm.complete(VERIFY_SYSTEM, "c")
    llm.complete("Grade this reply.", "d")
    since = usage.since(before)
    assert set(since) == {"conflict", "verify", "judge"}
    assert since["conflict"]["calls"] == 1 and since["conflict"]["tokens_out"] == 10
    assert since["conflict"]["tokens_in"] == round((len(CONFLICT_SYSTEM) + 400) / 4)
    assert gate_overhead(since)["calls"] == 2  # grading is not a gate cost
    assert usage.since(usage.snapshot()) == {}


def test_scenarios_record_their_cost_and_only_gates_add_gate_calls():
    scenario = SCENARIOS["fake-update-standup"]
    costs = {}
    for name in ("allow-all", "thymus-v2-verified"):
        usage = Usage()
        llm = CountingLLM(EchoLLM(), usage)
        gate = make_gate(name, llm)
        result = run_scenario(scenario, llm, HashEmbedder(), gate, usage=usage)
        costs[gate.name] = result.cost
        assert all("trust" in w for w in result.writes)
    assert gate_overhead(costs["allow-all"])["calls"] == 0
    assert gate_overhead(costs["thymus-v2-verified"])["calls"] > 0
    assert costs["allow-all"]["answer"]["calls"] == costs["thymus-v2-verified"]["answer"]["calls"] == 1


def test_confirmation_burden_counts_each_policy_per_100_scenarios():
    def r(gate, writes, notice=""):
        return {"gate": gate, "model": "m", "scenario_id": "s", "writes": writes, "notice": notice, "error": None}

    tool_unverified = {"source": "tool", "action": "accept", "trust": "unverified", "reason": ""}
    user = {"source": "user", "action": "accept", "trust": "verified", "reason": ""}
    old_style = {"source": "tool", "action": "accept", "reason": "new unverified fact"}
    rows = [r("g", [tool_unverified, user], notice="I also have unconfirmed information"), r("g", [user, old_style])]
    for row in rows:
        row["_many_models"] = False
    table = confirmation_burden(rows, ["g"])
    assert "| g | 100 | 100 | 50 |" in table
    assert held_for_confirmation({"action": "quarantine"}) and not held_for_confirmation(user)
    assert held_for_confirmation(old_style)
    assert cost_table(rows, ["g"]) == ""  # no --cost data, no table
