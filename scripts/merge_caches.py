"""Merge response caches from several Kaggle runs into one cache.tar.gz.

Usage: uv run python scripts/merge_caches.py out.tar.gz results/kaggle/*/cache.tar.gz
Entries are keyed by the full request, so merging never changes an answer; the first copy of
each key is kept. Pass the result to scripts/kaggle_push.sh so finished calls are reused.
"""

from __future__ import annotations

import io
import json
import sys
import tarfile
from pathlib import Path


def main() -> None:
    out, sources = Path(sys.argv[1]), [Path(p) for p in sys.argv[2:]]
    merged: dict[str, dict[str, str]] = {}
    for source in sources:
        with tarfile.open(source, "r:gz") as archive:
            for member in archive.getmembers():
                if member.isfile() and member.name.endswith(".jsonl") and "/llm/" in member.name \
                        and not Path(member.name).name.startswith("._"):  # macOS metadata files
                    entries = merged.setdefault(Path(member.name).name, {})
                    for line in archive.extractfile(member).read().decode().splitlines():
                        if line.strip():
                            entry = json.loads(line)
                            entries.setdefault(entry["key"], line)
    with tarfile.open(out, "w:gz") as archive:
        for name, entries in merged.items():
            data = ("\n".join(entries.values()) + "\n").encode()
            info = tarfile.TarInfo(f".cache/llm/{name}")
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
            print(f"{name}: {len(entries)} responses")


if __name__ == "__main__":
    main()
