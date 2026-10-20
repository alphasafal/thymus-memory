#!/bin/sh
# Download finished Kaggle runs and unpack them where thymus-report and paper_numbers.py look.
# Usage: scripts/kaggle_pull.sh <config-slug> ...   (e.g. qwen3-verified verifier-check2)
# Each run lands in results/kaggle/<slug>/{results/,cache.tar.gz,*.log}.
# Afterwards results/kaggle/cache.tar.gz is rebuilt from every downloaded cache.
set -eu
cd "$(dirname "$0")/.."
USER_NAME="safalguptaofficial"
for slug in "$@"; do
  kernel="thymus-run-$(echo "$slug" | tr '.' '-')"
  status=$(kaggle kernels status "$USER_NAME/$kernel" 2>&1 || true)
  case "$status" in
    *COMPLETE*) ;;
    *) echo "skip $slug: $status"; continue ;;
  esac
  out="results/kaggle/$slug"
  mkdir -p "$out"
  kaggle kernels output "$USER_NAME/$kernel" -p "$out" -o >/dev/null
  if [ -f "$out/results.tar.gz" ]; then
    tar -xzf "$out/results.tar.gz" -C "$out"
    echo "$slug: $(find "$out/results" -name results.jsonl | wc -l | tr -d ' ') result files"
  else
    echo "$slug: no results.tar.gz (see $out/$kernel.log)"
  fi
done
caches=$(ls results/kaggle/*/cache.tar.gz 2>/dev/null || true)
[ -n "$caches" ] && uv run python scripts/merge_caches.py results/kaggle/cache.tar.gz $caches
