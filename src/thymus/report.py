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

    # What disclosure costs the user: how often an answer carries a system notice, and how
    # often an update reaches the user only through one.
    print("\n### Disclosure burden: answers carrying a system notice\n")
    print("| Gate | Recall/benign | Updates | Attacks | Updates answered only in the notice |")
    print("|---|---|---|---|---|")
    for row_label in labels:
        def noticed(group):
            return pct([bool(r.get("notice")) for r in group if label(r) == row_label])
        only = [bool(r.get("update_in_notice")) and not r["passed"] for r in updates if label(r) == row_label]
        print(f"| {row_label} | {noticed(benign)} | {noticed(updates)} | {noticed(attacks)} | {pct(only)} |")

    print(confirmation_burden(rows, labels))
    print(cost_table(rows, labels))
    return 0


def held_for_confirmation(write: dict) -> bool:
    """A write the gate did not trust: quarantined, or stored unverified (results saved before
    writes recorded their trust say so in the reason)."""
    if write.get("action") == "quarantine":
        return True
    if "trust" in write:
        return write["trust"] == "unverified"
    return write.get("action") == "accept" and "unverified" in write.get("reason", "")


def confirmation_burden(rows: list[dict], labels: list[str]) -> str:
    """How often the user would be asked, under three ways of involving them:
    confirm every memory that came from outside the user (the safe default the paper argues
    against), confirm only what this gate did not trust, or (v2) disclose a contested claim
    only when an answer depends on it. Counts are per 100 scenarios; no model calls needed."""
    out = ["\n### Confirmation burden: user questions per 100 scenarios\n",
           "| Gate | Confirm every outside memory | Confirm what the gate distrusts | Disclose at answer time |",
           "|---|---|---|---|"]
    for row_label in labels:
        counts = burden_counts([r for r in rows if label(r) == row_label])
        if counts:
            out.append(f"| {row_label} | {counts[0]:.0f} | {counts[1]:.0f} | {counts[2]:.0f} |")
    return "\n".join(out)


def burden_counts(rows: list[dict]) -> tuple[float, float, float] | None:
    """User questions per 100 scenarios: confirm every outside memory, confirm what the gate
    distrusts, disclose at answer time."""
    rs = [r for r in rows if not r.get("error")]
    if not rs:
        return None
    n = len(rs) / 100
    outside = sum(1 for r in rs for w in r.get("writes", []) if w.get("source") == "tool")
    distrusted = sum(1 for r in rs for w in r.get("writes", []) if held_for_confirmation(w))
    notices = sum(1 for r in rs if r.get("notice"))
    return outside / n, distrusted / n, notices / n


def cost_table(rows: list[dict], labels: list[str]) -> str:
    """Model use added by each gate, from runs made with `thymus-eval --cost`."""
    from thymus.cost import gate_overhead

    measured = [r for r in rows if r.get("cost")]
    if not measured:
        return ""
    out = ["\n### Cost: gate-only model use (classify, conflict, verify)\n",
           "| Gate | Writes / scenario | Gate calls / write | Gate tokens / write | Gate seconds / write | "
           "Agent calls / scenario |", "|---|---|---|---|---|---|"]
    for row_label in labels:
        rs = [r for r in measured if label(r) == row_label]
        writes = sum(len(r.get("writes", [])) for r in rs)
        if not rs or not writes:
            continue
        over = [gate_overhead(r["cost"]) for r in rs]
        agent_calls = sum(r["cost"].get(j, {}).get("calls", 0) for r in rs for j in ("extract", "answer"))
        out.append(f"| {row_label} | {writes / len(rs):.1f} | {sum(o['calls'] for o in over) / writes:.2f} | "
                   f"{sum(o['tokens'] for o in over) / writes:.0f} | {sum(o['seconds'] for o in over) / writes:.2f} | "
                   f"{agent_calls / len(rs):.1f} |")
    out.append("\nTokens are estimated as characters / 4. Seconds are real only for uncached runs (`--no-cache`).")
    return "\n".join(out)


if __name__ == "__main__":
    sys.exit(main())
