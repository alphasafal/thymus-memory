import json

from thymus.report import bootstrap_ci, load, main, mcnemar_p


def row(scenario_id, gate, category="attack", poison_used=False, passed=True, **extra):
    return {
        "scenario_id": scenario_id, "category": category, "kind": "k", "gate": gate, "repeat": 0,
        "passed": passed, "poison_used": poison_used if category == "attack" else None,
        "poison_stored": poison_used if category == "attack" else None, "flagged": False,
        "flagged_lenient": False, "stale_leak": None, "error": None, **extra,
    }


def write_run(folder, model, rows):
    folder.mkdir(parents=True)
    (folder / "meta.json").write_text(json.dumps({"agent_model": model}))
    (folder / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))


def test_exact_mcnemar():
    assert mcnemar_p(0, 0) == 1.0
    assert mcnemar_p(0, 6) == 2 / 64  # all six discordant pairs favour one side
    assert mcnemar_p(3, 3) == 1.0


def test_bootstrap_interval_contains_the_rate_and_is_deterministic():
    rows = [row(f"fam{i}--attack", "g", poison_used=i % 2 == 0) for i in range(20)]
    low, high = bootstrap_ci(rows, lambda r: r["poison_used"])
    assert low <= 0.5 <= high and (low, high) == bootstrap_ci(rows, lambda r: r["poison_used"])
    assert bootstrap_ci(rows[:1], lambda r: r["poison_used"]) is None


def test_a_resumed_run_keeps_only_the_latest_row_and_models_stay_apart(tmp_path):
    write_run(tmp_path / "a" / "20261006-000000", "ollama:x", [row("f--attack", "thymus", poison_used=True)])
    write_run(tmp_path / "a" / "20261006-080000", "ollama:x", [row("f--attack", "thymus", poison_used=False)])
    write_run(tmp_path / "b" / "20261006-090000", "codex:y", [row("f--attack", "thymus", poison_used=True)])
    rows = load([tmp_path])
    by_model = {r["model"]: r["poison_used"] for r in rows}
    assert len(rows) == 2 and by_model == {"ollama:x": False, "codex:y": True}


def test_report_prints_paired_tests(tmp_path, capsys):
    rows = []
    for i in range(8):
        rows.append(row(f"fam{i}--attack", "allow-all", poison_used=True))
        rows.append(row(f"fam{i}--attack", "thymus", poison_used=False))
    write_run(tmp_path / "run", "ollama:x", rows)
    assert main([str(tmp_path), "--split", "all"]) == 0
    out = capsys.readouterr().out
    assert "| ollama:x | allow-all | Attack success | 100% | 0% | 8 | 0 | 0.008 |" in out
