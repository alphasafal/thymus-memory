"""Score the pairwise conflict verifier on labelled pairs (eval/verifier_pairs.jsonl).

Usage: uv run python scripts/verifier_check.py --llm ollama:qwen3:4b-instruct [--out results/verifier]

Pairs were taken from earlier runs' verifier calls and labelled without a model:
- conflict: the older fact holds the scenario's old value and the newer one its new value
  (benchmark and real Enron scenarios, matched by their markers),
- no conflict: one fact is a haystack background fact, which by construction is about a
  different thing.
Each wording (first, current) is scored on the same pairs: how many real conflicts it keeps
and how many non-conflicts it drops.
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from thymus.cli import make_llm
from thymus.conflicts import VERIFY_SCHEMA, VERIFY_SCHEMA_FIRST, VERIFY_SYSTEM, VERIFY_SYSTEM_FIRST
from thymus.llm import CachedLLM

WORDINGS = {"first": (VERIFY_SYSTEM_FIRST, VERIFY_SCHEMA_FIRST), "current": (VERIFY_SYSTEM, VERIFY_SCHEMA)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm", required=True)
    parser.add_argument("--pairs", type=Path, default=Path("eval/verifier_pairs.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("results/verifier"))
    args = parser.parse_args()
    llm = CachedLLM(make_llm(args.llm), Path(".cache/llm"))
    pairs = {(p["a"], p["b"]): p for p in map(json.loads, args.pairs.read_text().splitlines())}
    rows, tally = [], collections.Counter()
    for p in pairs.values():
        row = {k: p[k] for k in ("a", "b", "conflict", "source", "scenario")}
        for name, (system, schema) in WORDINGS.items():
            raw = llm.complete(system, f"<a>\n{p['a']}\n</a>\n\n<b>\n{p['b']}\n</b>", schema=schema)
            try:
                answer = json.loads(raw)
                confirmed = bool(answer.get("same_thing")) and bool(answer.get("different_values"))
            except (json.JSONDecodeError, AttributeError):
                answer, confirmed = raw, True
            row[name] = {"confirmed": confirmed, "answer": answer}
            tally[(p["source"], p["conflict"], name, confirmed)] += 1
        rows.append(row)
    args.out.mkdir(parents=True, exist_ok=True)
    slug = args.llm.replace(":", "_").replace("/", "_")
    (args.out / f"{slug}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    lines = [f"**Verifier:** `{args.llm}` · {len(rows)} pairs", "",
             "| Pairs | n | first wording keeps | current wording keeps |", "|---|---|---|---|"]
    for source in sorted({p["source"] for p in pairs.values()}):
        for conflict in (True, False):
            n = sum(1 for p in pairs.values() if p["source"] == source and p["conflict"] == conflict)
            if n:
                cells = [f"{tally[(source, conflict, w, True)]} / {n}" for w in WORDINGS]
                lines.append(f"| {source}, {'real conflict' if conflict else 'not a conflict'} | {n} | {cells[0]} | {cells[1]} |")
    lines.append("\nKeeping a real conflict is right; keeping a non-conflict is a false contest.")
    (args.out / f"{slug}.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
