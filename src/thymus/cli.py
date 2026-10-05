"""Command line entry point: `thymus-eval`."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from thymus.embed import Embedder, HashEmbedder, OllamaEmbedder
from thymus.gates import GATES, make_gate
from thymus.harness import run_scenario, summarize, summary_markdown
from thymus.judge import Judge
from thymus.llm import LLM, AnthropicLLM, CachedLLM, ClaudeCodeLLM, EchoLLM, OllamaLLM
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
    raise ValueError(f"unknown model spec {spec!r}; use echo, ollama:<model>, claude-code[:<model>] or anthropic:<model>")


def make_embedder(spec: str) -> Embedder:
    kind, _, model = spec.partition(":")
    if kind == "hash":
        return HashEmbedder()
    if kind == "ollama":
        return OllamaEmbedder(model or "nomic-embed-text")
    raise ValueError(f"unknown embedder spec {spec!r}; use hash or ollama:<model>")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="thymus-eval", description="Score memory write-gates on attack, update and benign scenarios.")
    parser.add_argument("--llm", default="ollama:qwen2.5:3b-instruct", help="agent model: echo | ollama:<model> | claude-code[:<model>] | anthropic:<model> (default: %(default)s)")
    parser.add_argument("--judge", default="same", help="grader: same (as --llm) | none (keywords only) | any --llm spec (default: %(default)s)")
    parser.add_argument("--embedder", default="ollama:nomic-embed-text", help="hash | ollama:<model> (default: %(default)s)")
    parser.add_argument("--gate", action="append", choices=list(GATES), help="gate to evaluate; repeat for several (default: all)")
    parser.add_argument("--scenarios", type=Path, default=Path("scenarios"), help="scenario file or folder (default: %(default)s)")
    parser.add_argument("--category", choices=CATEGORIES, action="append", help="only run these categories")
    parser.add_argument("--only", help="only run scenarios whose id contains this text")
    parser.add_argument("--repeats", type=int, default=1, help="runs per scenario (local models run at temperature 0, so repeats are identical)")
    parser.add_argument("--out", type=Path, default=Path("results"), help="folder for results (default: %(default)s)")
    parser.add_argument("--cache", type=Path, default=Path(".cache/llm"), help="response cache folder (default: %(default)s)")
    parser.add_argument("--no-cache", action="store_true", help="always call the model")
    args = parser.parse_args(argv)

    scenarios = load_scenarios(args.scenarios)
    if args.category:
        scenarios = [s for s in scenarios if s.category in args.category]
    if args.only:
        scenarios = [s for s in scenarios if args.only in s.id]
    if not scenarios:
        print("no scenarios matched", file=sys.stderr)
        return 1

    def cached(model: LLM) -> LLM:
        return model if args.no_cache or isinstance(model, EchoLLM) else CachedLLM(model, args.cache)

    llm = cached(make_llm(args.llm))
    embedder = make_embedder(args.embedder)
    gates = [make_gate(name, llm) for name in (args.gate or list(GATES))]
    judge = None
    if args.judge != "none" and not (args.judge == "same" and isinstance(llm, EchoLLM)):
        judge = Judge(llm if args.judge == "same" else cached(make_llm(args.judge)))

    run_dir = args.out / datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    results = []
    total = len(gates) * len(scenarios) * args.repeats
    with (run_dir / "results.jsonl").open("w") as log:
        for gate in gates:
            for scenario in scenarios:
                for repeat in range(args.repeats):
                    result = run_scenario(scenario, llm, embedder, gate, repeat, judge)
                    results.append(result)
                    log.write(json.dumps(asdict(result)) + "\n")
                    log.flush()
                    status = "ERROR" if result.error else ("pass" if result.passed else "FAIL")
                    print(f"[{len(results)}/{total}] {gate.name:<20} {scenario.id:<32} {status}", file=sys.stderr)

    grader = f"`{judge.name}`" if judge else "keywords"
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
    errors = [r for r in results if r.error]
    if errors:
        print(f"{len(errors)} runs errored; first error: {errors[0].error}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
