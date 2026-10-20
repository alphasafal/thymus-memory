"""Score the pairwise conflict verifier on labelled pairs (eval/verifier_pairs.jsonl).

Usage: uv run python scripts/verifier_check.py --llm ollama:qwen3:4b-instruct [--out results/verifier]

Pairs were taken from earlier runs' verifier calls and labelled without a model:
- conflict: the older fact holds the scenario's old value and the newer one its new value
  (benchmark and real Enron scenarios, matched by their markers),
- no conflict: a scenario fact against the most similar background memory from an unrelated
  family, and the most similar pairs of unrelated background memories (eval/haystack_related.json).
Pairs are split in two halves by family: a wording is chosen on half A and reported on half B.
Each wording is scored on the same pairs: real conflicts kept, non-conflicts dropped.
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from thymus.cli import make_llm
from thymus.conflicts import VERIFY_WORDINGS as WORDINGS
from thymus.llm import CachedLLM


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
        row = {k: p[k] for k in ("a", "b", "conflict", "source", "scenario", "split")}
        for name, (system, schema) in WORDINGS.items():
            raw = llm.complete(system, f"<a>\n{p['a']}\n</a>\n\n<b>\n{p['b']}\n</b>", schema=schema)
            try:
                answer = json.loads(raw)
                confirmed = bool(answer.get("same_thing")) and bool(answer.get("different_values"))
            except (json.JSONDecodeError, AttributeError):
                answer, confirmed = raw, True
            row[name] = {"confirmed": confirmed, "answer": answer}
            tally[(p["split"], p["source"], p["conflict"], name, confirmed)] += 1
        rows.append(row)
    args.out.mkdir(parents=True, exist_ok=True)
    slug = args.llm.replace(":", "_").replace("/", "_")
    (args.out / f"{slug}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    lines = [f"**Verifier:** `{args.llm}` · {len(rows)} pairs; cells: kept / n", ""]
    for half in ("A", "B"):
        lines += [f"Half {half}" + (" (choose here)" if half == "A" else " (report here)"), "",
                  "| Pairs | n | " + " | ".join(WORDINGS) + " |", "|---|---|" + "---|" * len(WORDINGS)]
        for source in sorted({p["source"] for p in pairs.values()}):
            for conflict in (True, False):
                n = sum(1 for p in pairs.values() if p["split"] == half and p["source"] == source and p["conflict"] == conflict)
                if n:
                    cells = [f"{tally[(half, source, conflict, w, True)]}" for w in WORDINGS]
                    kind = "real conflict" if conflict else "not a conflict"
                    lines.append(f"| {source}, {kind} | {n} | " + " | ".join(cells) + " |")
        lines.append("")
    lines.append("Keeping a real conflict is right; keeping a non-conflict is a false contest.")
    (args.out / f"{slug}.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
