"""`thymus-regrade`: grade saved replies again with the current grader.

The agent's replies are kept in every results.jsonl, so a grader fix does not need the
agent again (no subscription calls). Each run folder X gets a sibling X-regraded with the
same rows and new grades; `thymus-report` prefers it because it sorts after X. Whether
the poison was stored is a property of the memory, not the reply, so it is kept as is.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from thymus.cli import make_llm
from thymus.harness import ScenarioResult, apply_verdict
from thymus.judge import MODES, Judge
from thymus.llm import CachedLLM, LLMError, LLMUnavailable
from thymus.scenarios import load_scenarios

SUFFIX = "-regraded"


def run_files(paths: list[Path]) -> list[Path]:
    files = []
    for path in paths:
        files += sorted(path.rglob("results.jsonl")) if path.is_dir() else [path]
    return [f for f in files if not f.parent.name.endswith(SUFFIX)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="thymus-regrade", description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="results.jsonl files or folders containing them")
    parser.add_argument("--judge", default="ollama:qwen3:4b-instruct", help="grader model spec (default: %(default)s)")
    parser.add_argument("--grading", choices=MODES, default="hybrid")
    parser.add_argument("--scenarios", type=Path, default=Path("scenarios"))
    parser.add_argument("--cache", type=Path, default=Path(".cache/llm"))
    args = parser.parse_args(argv)

    scenarios = {s.id: s for s in load_scenarios(args.scenarios)}
    judge_llm = None if args.grading == "keywords" else CachedLLM(make_llm(args.judge), args.cache)
    judge = Judge(judge_llm, args.grading)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()

    for file in run_files(args.paths):
        rows = [json.loads(line) for line in file.read_text().splitlines() if line.strip()]
        changed = 0
        out_rows = []
        for row in rows:
            result = ScenarioResult(**row)
            scenario = scenarios.get(result.scenario_id)
            if scenario is not None and result.error is None and result.reply:
                before = result.judge_verdict
                try:
                    apply_verdict(scenario, result, judge.grade_reply(scenario, result.reply))
                    result.judge_error = None
                except LLMUnavailable as e:
                    print(f"stopped: grader unavailable: {e}", file=sys.stderr)
                    return 3
                except LLMError as e:
                    result.judge_error = str(e)
                changed += result.judge_verdict != before
            out_rows.append(asdict(result))

        out_dir = file.parent.with_name(file.parent.name + SUFFIX)
        out_dir.mkdir(exist_ok=True)
        meta_file = file.parent / "meta.json"
        meta = json.loads(meta_file.read_text()) if meta_file.exists() else {}
        meta.update({"grader": judge.name, "regraded_from": str(file.parent),
                     "regraded_at": datetime.now().isoformat(timespec="seconds"), "regraded_commit": commit})
        (out_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
        (out_dir / "results.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out_rows))
        print(f"{file.parent}: {len(rows)} rows, {changed} verdicts changed -> {out_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
