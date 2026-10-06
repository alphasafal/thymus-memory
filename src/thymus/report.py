"""`thymus-report`: tables for the paper from one or more results.jsonl files."""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean


def load(paths: list[Path]) -> list[dict]:
    """Rows from every results.jsonl, tagged with the agent model from the run's meta.json.

    A resumed run writes a new timestamped folder that repeats the scenarios it got from the
    cache, so each (model, gate, scenario, repeat) keeps only its latest row.
    """
    files = []
    for path in paths:
        files += sorted(path.rglob("results.jsonl")) if path.is_dir() else [path]
    latest: dict[tuple, dict] = {}
    for file in sorted(set(files), key=lambda f: (f.parent.name, str(f))):
        meta = json.loads((file.parent / "meta.json").read_text()) if (file.parent / "meta.json").exists() else {}
        model = meta.get("agent_model", "?")
        if meta.get("haystack"):
            model += f" +{meta['haystack']} background"  # long-memory runs are a separate condition
        for line in file.read_text().splitlines():
            if line.strip():
                row = json.loads(line)
                row["model"] = model
                latest[(model, row["gate"], row["scenario_id"], row.get("repeat", 0))] = row
    return [r for r in latest.values() if r.get("error") is None]


def family(scenario_id: str) -> str:
    return scenario_id.split("--")[0]


def bootstrap_ci(rows: list[dict], metric, resamples: int = 2000, seed: int = 0) -> tuple[float, float] | None:
    """95% interval for a rate, resampling whole scenario families: the recall, update and
    attack versions of a family (and its language versions) are not independent runs."""
    by_family: dict[str, list] = defaultdict(list)
    for r in rows:
        value = metric(r)
        if value is not None:
            by_family[family(r["scenario_id"])].append(float(value))
    families = list(by_family)
    if len(families) < 2:
        return None
    rng = random.Random(seed)
    stats = []
    for _ in range(resamples):
        values = [v for _ in families for v in by_family[families[rng.randrange(len(families))]]]
        stats.append(sum(values) / len(values))
    stats.sort()
    return stats[int(0.025 * resamples)], stats[int(0.975 * resamples) - 1]


def mcnemar_p(worse: int, better: int) -> float:
    """Exact two-sided McNemar test on the discordant pairs."""
    n = worse + better
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(worse, better) + 1)) / 2**n
    return min(1.0, 2 * tail)


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


def pct_ci(rows: list[dict], metric) -> str:
    """Rate, 95% family-bootstrap interval and number of runs."""
    known = [metric(r) for r in rows if metric(r) is not None]
    if not known:
        return "–"
    ci = bootstrap_ci(rows, metric)
    interval = f" [{ci[0]:.0%}–{ci[1]:.0%}]" if ci else ""
    return f"{mean(known):.0%}{interval} ({len(known)})"


def label(r: dict) -> str:
    """Table row name: the gate, prefixed by the agent model when several models are loaded."""
    return f"{r['model']} · {r['gate']}" if r.get("_many_models") else r["gate"]


def table(title: str, rows: list[dict], key, columns: list[tuple[str, callable]]) -> str:
    labels = list(dict.fromkeys(label(r) for r in rows))
    groups = sorted({key(r) for r in rows if key(r)})
    out = [f"### {title}", ""]
    for name, metric in columns:
        out += [f"**{name}**", "", "| Gate | " + " | ".join(groups) + " |", "|---|" + "---|" * len(groups)]
        for row_label in labels:
            cells = [pct([metric(r) for r in rows if label(r) == row_label and key(r) == g]) for g in groups]
            out.append(f"| {row_label} | " + " | ".join(cells) + " |")
        out.append("")
    return "\n".join(out)


PAIRED_METRICS = (
    # name, category, outcome where True is bad, so "better" means fewer True
    ("Attack success", "attack", lambda r: r["poison_used"], True),
    ("Update accuracy", "update", lambda r: r["passed"], False),
    ("Recall accuracy", "benign", lambda r: r["passed"], False),
)


def paired_tests(rows: list[dict], gate: str = "thymus") -> str:
    """Thymus against each other gate on the same scenarios, per model (exact McNemar)."""
    out = [f"### {gate} against each baseline (paired by scenario, exact McNemar)", "",
           f"| Model | Baseline | Metric | Baseline rate | {gate} rate | {gate} better | {gate} worse | p |",
           "|---|---|---|---|---|---|---|---|"]
    found = False
    for model in dict.fromkeys(r["model"] for r in rows):
        mine = {(r["scenario_id"], r.get("repeat", 0)): r for r in rows if r["model"] == model and r["gate"] == gate}
        if not mine:
            continue
        for baseline in dict.fromkeys(r["gate"] for r in rows if r["model"] == model and r["gate"] != gate):
            theirs = {(r["scenario_id"], r.get("repeat", 0)): r for r in rows if r["model"] == model and r["gate"] == baseline}
            for name, category, metric, true_is_bad in PAIRED_METRICS:
                pairs = [(metric(theirs[k]), metric(mine[k])) for k in mine.keys() & theirs.keys()
                         if mine[k]["category"] == category and metric(mine[k]) is not None and metric(theirs[k]) is not None]
                if not pairs:
                    continue
                found = True
                better = sum(1 for b, t in pairs if b != t and bool(t) != true_is_bad)
                worse = sum(1 for b, t in pairs if b != t and bool(t) == true_is_bad)
                p = mcnemar_p(worse, better)
                out.append(
                    f"| {model} | {baseline} | {name} | {mean(bool(b) for b, _ in pairs):.0%} | "
                    f"{mean(bool(t) for _, t in pairs):.0%} | {better} | {worse} | "
                    f"{'<0.001' if p < 0.001 else f'{p:.3f}'} |"
                )
    out.append("")
    return "\n".join(out) if found else ""


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

    many_models = len({r["model"] for r in rows}) > 1
    for r in rows:
        r["_many_models"] = many_models
    attacks = [r for r in rows if r["category"] == "attack"]
    updates = [r for r in rows if r["category"] == "update"]
    benign = [r for r in rows if r["category"] == "benign"]
    labels = list(dict.fromkeys(label(r) for r in rows))

    print(f"## Main results ({args.split} split, {len({r['scenario_id'] for r in rows})} scenarios)\n")
    print("| Gate | Attack success ↓ (strict) | Attack success (lenient) | Attack flagged | Attack stored ↓ | Update accuracy ↑ | Stale answer ↓ | Recall/benign accuracy ↑ |")
    print("|---|---|---|---|---|---|---|---|")
    for row_label in labels:
        a = [r for r in attacks if label(r) == row_label]
        u = [r for r in updates if label(r) == row_label]
        b = [r for r in benign if label(r) == row_label]
        print(
            f"| {row_label} | {pct_ci(a, lambda r: r['poison_used'])} | "
            f"{pct([r['poison_used'] and not r.get('flagged_lenient') if r['poison_used'] is not None else None for r in a])} | "
            f"{pct([r['flagged'] for r in a])} | "
            f"{pct([r['poison_stored'] for r in a])} | {pct_ci(u, lambda r: r['passed'])} | "
            f"{pct([r['stale_leak'] for r in u])} | {pct_ci(b, lambda r: r['passed'])} |"
        )
    print("\nCells show the rate, a 95% interval from resampling scenario families (main metrics), "
          "and in brackets the number of runs.\n")
    print(paired_tests(rows))

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
    for row_label in labels:
        a = [r for r in attacks if label(r) == row_label and r["poison_stored"] is not None]
        counts = defaultdict(int)
        for r in a:
            counts[(bool(r["poison_stored"]), bool(r["poison_used"]))] += 1
        n = len(a) or 1
        print(
            f"| {row_label} | {counts[(True, True)] / n:.0%} | {counts[(True, False)] / n:.0%} | "
            f"{counts[(False, True)] / n:.0%} | {counts[(False, False)] / n:.0%} |"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
