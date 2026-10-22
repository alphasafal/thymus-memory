"""A fixed, stratified sample of MemForm cases: N per attack interface (seed 0).

Usage: python scripts/memform_sample.py <accepted_cases.jsonl> <out.jsonl> [N]
"""

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

source, out = sys.argv[1], sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 30
by_interface = defaultdict(list)
for line in open(source):
    if line.strip():
        case = json.loads(line)
        by_interface[case["interface"]].append(case)
rng = random.Random(0)
picked = [c for k in sorted(by_interface) for c in rng.sample(by_interface[k], min(n, len(by_interface[k])))]
Path(out).parent.mkdir(parents=True, exist_ok=True)
with open(out, "w") as f:
    f.writelines(json.dumps(c) + "\n" for c in picked)
print(f"{len(picked)} cases: " + ", ".join(f"{k} {min(n, len(v))}" for k, v in sorted(by_interface.items())))
