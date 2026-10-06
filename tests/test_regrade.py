import json

from thymus.cli import main as run_eval
from thymus.regrade import main as regrade
from thymus.report import load


def test_regrade_writes_a_sibling_folder_that_the_report_prefers(tmp_path):
    out = tmp_path / "run"
    assert run_eval(["--llm", "echo", "--embedder", "hash", "--only", "standup-time--", "--gate", "allow-all",
                     "--out", str(out), "--no-cache", "--judge", "none"]) == 0
    original = next(out.rglob("results.jsonl"))
    rows = [json.loads(line) for line in original.read_text().splitlines()]
    # Pretend an old grader called every reply "other".
    for row in rows:
        row["judge_verdict"], row["passed"] = "other", False
    original.write_text("".join(json.dumps(r) + "\n" for r in rows))

    assert regrade([str(out), "--grading", "keywords"]) == 0
    regraded = original.parent.with_name(original.parent.name + "-regraded")
    assert (regraded / "results.jsonl").exists()
    assert json.loads((regraded / "meta.json").read_text())["regraded_from"] == str(original.parent)
    latest = {r["scenario_id"]: r for r in load([out])}
    assert len(latest) == 3 and latest["standup-time--recall"]["judge_verdict"] == "correct"
    # Regrading again reads only the original runs, never its own output.
    assert regrade([str(out), "--grading", "keywords"]) == 0
    assert len(list(out.rglob("results.jsonl"))) == 2
