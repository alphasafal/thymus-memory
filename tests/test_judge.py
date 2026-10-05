import json
import stat
from pathlib import Path

import pytest

from thymus.embed import HashEmbedder
from thymus.gates import AllowAllGate
from thymus.harness import run_scenario, summarize
from thymus.judge import Judge
from thymus.llm import ClaudeCodeLLM, EchoLLM, LLMError
from thymus.scenarios import load_scenarios

SCENARIOS = {s.id: s for s in load_scenarios(Path(__file__).parent.parent / "scenarios")}


class ScriptedJudgeLLM:
    """Answers grading prompts as if the reply had the given verdict."""

    name = "scripted-judge"
    ANSWERS = {
        "adopted": {"mentions_claim": True, "presents_as_true": True},
        "flagged": {"mentions_claim": True, "presents_as_true": False},
        "absent": {"mentions_claim": False, "presents_as_true": False},
        "correct": {"gives_correct_answer": True, "gives_outdated_answer": False},
        "outdated": {"gives_correct_answer": False, "gives_outdated_answer": True},
        "other": {"gives_correct_answer": False, "gives_outdated_answer": False},
    }

    def __init__(self, verdict: str, holds_claim: bool = False):
        self.verdict = verdict
        self.holds_claim = holds_claim

    def complete(self, system, prompt, schema=None):
        if "contains_claim" in json.dumps(schema):
            return json.dumps({"contains_claim": self.holds_claim, "reason": "scripted"})
        return json.dumps({**self.ANSWERS[self.verdict], "reason": "scripted"})


def run(scenario_id: str, judge_llm) -> object:
    return run_scenario(SCENARIOS[scenario_id], EchoLLM(), HashEmbedder(), AllowAllGate(), judge=Judge(judge_llm))


def test_judge_overrides_keywords_and_records_both():
    # The echo agent repeats the fake number, so keywords say the attack worked.
    result = run("web-fake-support-number", ScriptedJudgeLLM("flagged"))
    assert result.marker_passed is False
    assert result.passed is True and result.flagged is True and result.poison_used is False


def test_judge_checks_memory_for_reworded_poison_when_keywords_miss():
    judge_llm = ScriptedJudgeLLM("adopted", holds_claim=True)
    result = run("minja-refund-policy", judge_llm)
    assert result.poison_stored is True  # keyword hit already proves it; no extra call needed
    assert result.poison_used is True


def test_update_verdicts_map_to_metrics():
    result = run("user-moved-city", ScriptedJudgeLLM("outdated"))
    assert result.passed is False and result.stale_leak is True


def test_judge_failure_falls_back_to_keywords():
    class Broken:
        name = "broken"

        def complete(self, system, prompt, schema=None):
            return "not json"

    result = run("user-dog-name", Broken())
    assert result.judge_error and result.passed == result.marker_passed


def test_summary_reports_agreement():
    results = [run("web-fake-support-number", ScriptedJudgeLLM("flagged")), run("user-dog-name", ScriptedJudgeLLM("correct"))]
    summary = summarize(results)["allow-all"]
    assert summary["judge_marker_agreement"] == 0.5
    assert summary["attack_flagged_rate"] == 1.0


def fake_cli(tmp_path: Path, payload: dict) -> str:
    script = tmp_path / "claude"
    script.write_text(f"#!/bin/sh\ncat <<'EOF'\n{json.dumps(payload)}\nEOF\n")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return str(script)


def test_claude_code_llm_returns_structured_output(tmp_path):
    binary = fake_cli(tmp_path, {"is_error": False, "result": "", "structured_output": {"verdict": "correct", "reason": "ok"}})
    out = ClaudeCodeLLM(binary=binary).complete("sys", "prompt", schema={"type": "object"})
    assert json.loads(out)["verdict"] == "correct"


def test_claude_code_llm_surfaces_login_errors(tmp_path):
    binary = fake_cli(tmp_path, {"is_error": True, "result": "Not logged in · Please run /login"})
    with pytest.raises(LLMError, match="Not logged in"):
        ClaudeCodeLLM(binary=binary).complete("sys", "prompt")
