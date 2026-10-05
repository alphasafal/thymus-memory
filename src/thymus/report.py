"""`thymus-report`: tables for the paper from one or more results.jsonl files."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean


def load(paths: list[Path]) -> list[dict]:
    rows = []
    for path in paths:
        files = sorted(path.rglob("results.jsonl")) if path.is_dir() else [path]
        for file in files:
            rows += [json.loads(line) for line in file.read_text().splitlines() if line.strip()]
    return [r for r in rows if r.get("error") is None]


def dev_entries(path: Path) -> set[str]:
    if not path.exists():
        return set()
    lines = (line.split("#")[0].strip() for line in path.read_text().splitlines())
    return {line for line in lines if line}


def in_dev(scenario_id: str, dev: set[str]) -> bool:
    return scenario_id in dev or scenario_id.split("--")[0] in dev


def pct(values: list) -> str:
    known = [v for v in values if v is not None]
    return f"{mean(known):.0%} ({len(known)})" if known else "–"


def table(title: str, rows: list[dict], key, columns: list[tuple[str, callable]]) -> str:
    gates = list(dict.fromkeys(r["gate"] for r in rows))
    groups = sorted({key(r) for r in rows if key(r)})
    out = [f"### {title}", ""]
    for name, metric in columns:
        out += [f"**{name}**", "", "| Gate | " + " | ".join(groups) + " |", "|---|" + "---|" * len(groups)]
        for gate in gates:
            cells = [pct([metric(r) for r in rows if r["gate"] == gate and key(r) == g]) for g in groups]
            out.append(f"| {gate} | " + " | ".join(cells) + " |")
        out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="thymus-report", description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="results.jsonl files or folders containing them")
    parser.add_argument("--split", choices=("test", "dev", "all"), default="test",
                        help="test (default) excludes scenarios used during development")
    parser.add_argument("--dev-set", type=Path, default=Path("eval/dev_set.txt"))
    args = parser.parse_args(argv)
    rows = load(args.paths)
    dev = dev_entries(args.dev_set)
    if args.split == "test":
        rows = [r for r in rows if not in_dev(r["scenario_id"], dev)]
    elif args.split == "dev":
        rows = [r for r in rows if in_dev(r["scenario_id"], dev)]
    if not rows:
        print("no results found", file=sys.stderr)
        return 1

    attacks = [r for r in rows if r["category"] == "attack"]
    updates = [r for r in rows if r["category"] == "update"]
    benign = [r for r in rows if r["category"] == "benign"]
    gates = list(dict.fromkeys(r["gate"] for r in rows))

    print(f"## Main results ({args.split} split, {len({r['scenario_id'] for r in rows})} scenarios)\n")
    print("| Gate | Attack success ↓ (strict) | Attack success (lenient) | Attack flagged | Attack stored ↓ | Update accuracy ↑ | Stale answer ↓ | Recall/benign accuracy ↑ |")
    print("|---|---|---|---|---|---|---|---|")
    for gate in gates:
        a = [r for r in attacks if r["gate"] == gate]
        u = [r for r in updates if r["gate"] == gate]
        b = [r for r in benign if r["gate"] == gate]
        print(
            f"| {gate} | {pct([r['poison_used'] for r in a])} | "
            f"{pct([r['poison_used'] and not r.get('flagged_lenient') if r['poison_used'] is not None else None for r in a])} | "
            f"{pct([r['flagged'] for r in a])} | "
            f"{pct([r['poison_stored'] for r in a])} | {pct([r['passed'] for r in u])} | "
            f"{pct([r['stale_leak'] for r in u])} | {pct([r['passed'] for r in b])} |"
        )
    print("\nCells show the rate and, in brackets, the number of runs.\n")

    print(table("Attack success by attack type", attacks, lambda r: r["kind"], [("Attack success ↓", lambda r: r["poison_used"])]))
    print(table("Update accuracy by update source", updates, lambda r: r["kind"], [("Update accuracy ↑", lambda r: r["passed"])]))
    print(table("By language", attacks + updates + benign, lambda r: r.get("language", "en"), [
        ("Attack success ↓", lambda r: r["poison_used"] if r["category"] == "attack" else None),
        ("Update accuracy ↑", lambda r: r["passed"] if r["category"] == "update" else None),
        ("Recall accuracy ↑", lambda r: r["passed"] if r["category"] == "benign" else None),
    ]))
    by_domain = attacks + updates
    print(table("By topic (families only)", by_domain, lambda r: r.get("domain", ""), [
        ("Attack success ↓", lambda r: r["poison_used"] if r["category"] == "attack" else None),
        ("Update accuracy ↑", lambda r: r["passed"] if r["category"] == "update" else None),
    ]))

    # Where attacks get through: stored and used, stored but not used, never stored.
    print("### Where attacks get through\n")
    print("| Gate | Stored and adopted | Stored, not adopted | Not stored, still adopted | Blocked at write |")
    print("|---|---|---|---|---|")
    for gate in gates:
        a = [r for r in attacks if r["gate"] == gate and r["poison_stored"] is not None]
        counts = defaultdict(int)
        for r in a:
            counts[(bool(r["poison_stored"]), bool(r["poison_used"]))] += 1
        n = len(a) or 1
        print(
            f"| {gate} | {counts[(True, True)] / n:.0%} | {counts[(True, False)] / n:.0%} | "
            f"{counts[(False, True)] / n:.0%} | {counts[(False, False)] / n:.0%} |"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
