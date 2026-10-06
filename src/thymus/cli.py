"""Command line entry point: `thymus-eval`."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from thymus.embed import Embedder, HashEmbedder, OllamaEmbedder
from thymus.gates import GATES, MAIN_GATES, make_gate
from thymus.harness import run_scenario, summarize, summary_markdown
from thymus.judge import MODES, Judge
from thymus.llm import LLM, AnthropicLLM, CachedLLM, ClaudeCodeLLM, CodexLLM, EchoLLM, LLMUnavailable, OllamaLLM
from thymus.scenarios import CATEGORIES, load_scenarios


def make_llm(spec: str) -> LLM:
    kind, _, model = spec.partition(":")
    if kind == "echo":
        return EchoLLM()
    if kind == "ollama":
        return OllamaLLM(model or "qwen2.5:3b-instruct")
    if kind == "anthropic":
        return AnthropicLLM(model or "claude-opus-5-5")
    if kind == "claude-code":
        return ClaudeCodeLLM(model or None)
    if kind == "codex":
        return CodexLLM(model or None)
    raise ValueError(f"unknown model spec {spec!r}; use echo, ollama:<model>, claude-code[:<model>], codex[:<model>] or anthropic:<model>")


def preflight(llm: LLM) -> str | None:
    """A model that leaks its reasoning into answers (some 'thinking' builds do when
    thinking is switched off) silently ruins a whole run. Catch it with one cheap call."""
    if isinstance(llm, EchoLLM):
        return None
    reply = llm.complete("Answer with one word.", "What is the capital of France?")
    if "paris" not in reply.lower() or len(reply) > 80:
        return f"{llm.name} failed the sanity check (expected a one-word answer, got {reply[:120]!r})"
    return None


def run_metadata(args: argparse.Namespace, llm: LLM, judge: Judge, scenarios: list) -> dict:
    """Everything needed to reproduce a run: code version, settings, scenario set."""
    def git(*cmd: str) -> str:
        try:
            return subprocess.run(["git", *cmd], capture_output=True, text=True, timeout=10).stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            return ""

    return {
        "started": datetime.now().isoformat(timespec="seconds"),
        "git_commit": git("rev-parse", "HEAD"),
        "git_dirty": bool(git("status", "--porcelain", "--untracked-files=no")),
        "agent_model": llm.name,
        "grader": judge.name,
        "embedder": args.embedder,
        "gates": args.gate or list(GATES),
        "scenario_count": len(scenarios),
        "scenario_ids": [s.id for s in scenarios],
        "argv": sys.argv[1:],
    }


def make_embedder(spec: str) -> Embedder:
    kind, _, model = spec.partition(":")
    if kind == "hash":
        return HashEmbedder()
    if kind == "ollama":
        return OllamaEmbedder(model or "nomic-embed-text")
    raise ValueError(f"unknown embedder spec {spec!r}; use hash or ollama:<model>")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="thymus-eval", description="Score memory write-gates on attack, update and benign scenarios.")
    parser.add_argument("--llm", default="ollama:qwen2.5:3b-instruct", help="agent model: echo | ollama:<model> | claude-code[:<model>] | codex[:<model>] | anthropic:<model> (default: %(default)s)")
    parser.add_argument("--judge", default="same", help="grading model: same (as --llm) | none | any --llm spec (default: %(default)s)")
    parser.add_argument("--grading", choices=MODES, default="hybrid", help="how replies are graded (default: %(default)s)")
    parser.add_argument("--embedder", default="ollama:nomic-embed-text", help="hash | ollama:<model> (default: %(default)s)")
    parser.add_argument("--gate", action="append", choices=list(GATES), help="gate to evaluate; repeat for several (default: the six main gates, no ablations)")
    parser.add_argument("--scenarios", type=Path, default=Path("scenarios"), help="scenario file or folder (default: %(default)s)")
    parser.add_argument("--category", choices=CATEGORIES, action="append", help="only run these categories")
    parser.add_argument("--only", action="append", help="only run scenarios whose id contains this text; repeat for several")
    parser.add_argument("--repeats", type=int, default=1, help="runs per scenario (local models run at temperature 0, so repeats are identical)")
    parser.add_argument("--out", type=Path, default=Path("results"), help="folder for results (default: %(default)s)")
    parser.add_argument("--cache", type=Path, default=Path(".cache/llm"), help="response cache folder (default: %(default)s)")
    parser.add_argument("--no-cache", action="store_true", help="always call the model")
    parser.add_argument("--max-new-calls", type=int, help="stop after this many uncached model calls (agent and grader each)")
    args = parser.parse_args(argv)

    scenarios = load_scenarios(args.scenarios)
    if args.category:
        scenarios = [s for s in scenarios if s.category in args.category]
    if args.only:
        scenarios = [s for s in scenarios if any(text in s.id for text in args.only)]
    if not scenarios:
        print("no scenarios matched", file=sys.stderr)
        return 1

    def cached(model: LLM) -> LLM:
        if args.no_cache or isinstance(model, EchoLLM):
            return model
        return CachedLLM(model, args.cache, args.max_new_calls)

    llm = cached(make_llm(args.llm))
    embedder = make_embedder(args.embedder)
    problem = preflight(llm)
    if problem:
        print(problem, file=sys.stderr)
        return 2
    gates = [make_gate(name, llm) for name in (args.gate or MAIN_GATES)]
    judge_llm = None
    if args.judge != "none" and not (args.judge == "same" and isinstance(llm, EchoLLM)):
        judge_llm = llm if args.judge == "same" else cached(make_llm(args.judge))
    grading = args.grading if judge_llm is not None else "keywords"
    judge = Judge(judge_llm, grading)

    run_dir = args.out / datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "meta.json").write_text(json.dumps(run_metadata(args, llm, judge, scenarios), indent=2) + "\n")
    results = []
    total = len(gates) * len(scenarios) * args.repeats
    unavailable = None
    with (run_dir / "results.jsonl").open("w") as log:
        try:
            for gate in gates:
                for scenario in scenarios:
                    for repeat in range(args.repeats):
                        if any(getattr(m, "exhausted", False) for m in (llm, judge.llm)):
                            break
                        result = run_scenario(scenario, llm, embedder, gate, repeat, judge)
                        results.append(result)
                        log.write(json.dumps(asdict(result)) + "\n")
                        log.flush()
                        status = "ERROR" if result.error else ("pass" if result.passed else "FAIL")
                        print(f"[{len(results)}/{total}] {gate.name:<20} {scenario.id:<32} {status}", file=sys.stderr)
        except LLMUnavailable as e:
            unavailable = e

    grader = f"`{judge.name}`"
    header = (
        f"**Model:** `{llm.name}` · **Embedder:** `{embedder.name}` · **Grader:** {grader} · "
        f"**Scenarios:** {len(scenarios)} · **Repeats:** {args.repeats}"
    )
    summary = summarize(results)
    report = summary_markdown(summary, header)
    (run_dir / "summary.md").write_text(report + "\n")
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(report)
    print(f"\nSaved to {run_dir}", file=sys.stderr)
    if any(getattr(m, "exhausted", False) for m in (llm, judge.llm)):
        print(f"Stopped early: reached --max-new-calls {args.max_new_calls}. Rerun to resume from the cache.", file=sys.stderr)
    if unavailable:
        print(f"Stopped early, model server unavailable: {unavailable}. Rerun the same command to resume from the cache.", file=sys.stderr)
        return 3
    errors = [r for r in results if r.error]
    if errors:
        print(f"{len(errors)} runs errored; first error: {errors[0].error}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
