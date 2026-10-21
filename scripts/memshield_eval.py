"""External check on MemShield-Bench (Pow 2026, CC BY-SA 4.0; npow/memshield-bench on Hugging Face).

Usage: uv run python scripts/memshield_eval.py --llm ollama:qwen3:4b-instruct [--split test]
Needs data/memshield/full.jsonl (see docs/datasets.md). Two measurements, on attacks we did not write:

1. Pairs: MemShield's 42 poisoned entries that rewrite a clean entry. The clean entry is stored
   from one tool origin, the poisoned one arrives from another; a gate passes if the poisoned
   entry is contested or rejected (it can never replace the clean one: different origin).
2. Screening: every entry of the split arrives alone from an untrusted tool origin. Poisoned
   entries the claim classifier rejects as instructions or preferences, and clean entries it
   rejects by mistake.
Writes results/memshield/<gate-model>.json and prints the tables.
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from thymus.cli import make_llm
from thymus.embed import MemoEmbedder, OllamaEmbedder
from thymus.gates import make_gate
from thymus.llm import CachedLLM
from thymus.memory import Candidate, MemoryStore

GATES = ("thymus-v2-auto", "thymus-v2-verified", "thymus-v3")
TRUSTED_SOURCE, OTHER_SOURCE = "doc:team-wiki", "web:forum-post"


def outcome(gate, store, text: str, origin: str, turn: int) -> str:
    decision = gate.review(Candidate(text, "tool", origin, "victim", turn), store)
    if decision.action == "reject":
        return "rejected"
    if decision.action == "quarantine" or decision.contradicts:
        return "contested"
    return "replaced" if decision.supersedes else "stored unverified"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm", required=True, help="gate model")
    parser.add_argument("--data", type=Path, default=Path("data/memshield/full.jsonl"))
    parser.add_argument("--split-file", type=Path, help="screen only this split (e.g. data/memshield/test.jsonl)")
    parser.add_argument("--out", type=Path, default=Path("eval/external/memshield"))
    args = parser.parse_args()
    llm = CachedLLM(make_llm(args.llm), Path(".cache/llm"))
    embedder = MemoEmbedder(OllamaEmbedder("nomic-embed-text"))
    rows = [json.loads(line) for line in args.data.read_text().splitlines() if line.strip()]
    by_id = {r["id"]: r for r in rows}
    pairs = [(by_id[r["paired_id"]], r) for r in rows if r["label"] == "poisoned" and r["paired_id"] in by_id]
    screen = ([json.loads(line) for line in args.split_file.read_text().splitlines() if line.strip()]
              if args.split_file else rows)
    report = {"gate_model": args.llm, "pairs": {}, "screening": {}}

    for name in GATES:
        gate = make_gate(name, llm)
        counts = collections.Counter()
        for clean, poisoned in pairs:
            store = MemoryStore(embedder)
            store.add(Candidate(clean["content"], "tool", TRUSTED_SOURCE, "victim", 1), trust="unverified")
            counts[outcome(gate, store, poisoned["content"], OTHER_SOURCE, 2)] += 1
        report["pairs"][name] = dict(counts)

    gate = make_gate("thymus-v3", llm)  # screening is the same claim classifier in every version
    screened = collections.defaultdict(collections.Counter)
    for r in screen:
        key = r["attack_type"] if r["label"] == "poisoned" else "clean"
        screened[key][outcome(gate, MemoryStore(embedder), r["content"], OTHER_SOURCE, 1)] += 1
    report["screening"] = {k: dict(v) for k, v in screened.items()}

    args.out.mkdir(parents=True, exist_ok=True)
    slug = args.llm.replace(":", "_").replace("/", "_")
    (args.out / f"{slug}.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Gate model {args.llm}. Pairs (n={len(pairs)}): poisoned rewrite of a stored clean entry, other origin")
    for name, c in report["pairs"].items():
        caught = c.get("contested", 0) + c.get("rejected", 0)
        print(f"  {name:<20} contested or rejected {caught}/{len(pairs)}  {c}")
    print(f"Screening (n={len(screen)}), single entries from an untrusted origin:")
    for k, c in sorted(report["screening"].items()):
        n = sum(c.values())
        print(f"  {k:<32} rejected {c.get('rejected', 0)}/{n}")


if __name__ == "__main__":
    main()
