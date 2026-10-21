"""Fail if the paper still has a missing number or a pending sentence.

Usage: uv run python scripts/check_paper.py   (run after scripts/paper_numbers.py, before submitting)
"""

import re
import sys
from pathlib import Path

auto = Path("paper/numbers-auto.tex").read_text()
missing = sorted(set(re.findall(r"\\newcommand\{\\(\w+)\}\{--\}", auto)))
pending = [line.split("}{", 1)[0] for line in Path("paper/numbers.tex").read_text().splitlines()
           if "\\pending{" in line and not line.startswith("\\newcommand{\\pending}")]
for name in missing:
    print(f"missing number: \\{name}")
for line in pending:
    print(f"pending sentence: {line.removeprefix(chr(92) + 'newcommand{')}")
print(f"{len(missing)} missing numbers, {len(pending)} pending sentences")
sys.exit(1 if missing or pending else 0)
