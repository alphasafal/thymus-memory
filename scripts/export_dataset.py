"""Export the benchmark as flat JSONL for the Hugging Face dataset (dataset/).

Usage: uv run python scripts/export_dataset.py
Writes dataset/benchmark.jsonl (the 491 matched-pair scenarios, with their split) and
dataset/real.jsonl (scenarios built from public corpora, each with its source licence).
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from thymus.report import dev_entries, in_dev
from thymus.scenarios import load_scenarios

OUT = Path("dataset")
DEV = dev_entries(Path("eval/dev_set.txt"))
REAL_LICENCES = {
    "sms": "CC BY 4.0 (Mishra & Soni 2022, Mendeley Data f45bkkt8pr); links and numbers replaced",
    "email-phishing": "CC BY 4.0 (Nazario phishing corpus 2024-2025); links, addresses and numbers redacted",
    "enron-updates": "Enron corpus (CMU release 2015-05-07, public FERC record); names pseudonymised",
}


def row(scenario, **extra) -> dict:
    data = asdict(scenario)
    family, _, variant = scenario.id.rpartition("--")
    data["family"] = family if variant in ("recall", "legit", "attack") else ""
    data["split"] = "dev" if in_dev(scenario.id, DEV) else "test"
    return {**data, **extra}


def main() -> None:
    OUT.mkdir(exist_ok=True)
    bench = [row(s) for s in load_scenarios(Path("scenarios"))]
    (OUT / "benchmark.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in bench))
    real = []
    for path in sorted(Path("scenarios-real").glob("*.json")):
        real += [row(s, source=path.stem, licence=REAL_LICENCES[path.stem]) for s in load_scenarios(path)]
    (OUT / "real.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in real))
    splits = {k: sum(r["split"] == k for r in bench) for k in ("dev", "test")}
    print(f"benchmark: {len(bench)} scenarios {splits}; real: {len(real)} scenarios")


if __name__ == "__main__":
    main()
