#!/bin/sh
# Reproduce the paper's benchmark tables from the published response cache, on a laptop.
#
# Every model answer the paper used is in the cache, so no chat model or GPU is needed: only
# Ollama with the embedding model (about 270 MB). Each scenario is replayed through the same
# code, the cache serves every model call, and the tables are rebuilt from the replay.
# A cache miss (a changed prompt, or different embeddings changing what is recalled) would
# call the chat model; `--max-new-calls` is set high enough to finish but every miss is counted.
#
# Usage: scripts/reproduce.sh <cache.tar.gz> [qwen|llama|both]
set -eu
cd "$(dirname "$0")/.."
CACHE="${1:?usage: scripts/reproduce.sh <cache.tar.gz> [qwen|llama|both]}"
WHICH="${2:-both}"
OUT="results/reproduce"
GATES="allow-all user-only conflict-quarantine last-write-wins bounded-occupancy label-only thymus thymus-v2-auto thymus-v2-verified thymus-v3"

command -v ollama >/dev/null || { echo "install Ollama first: https://ollama.com" >&2; exit 1; }
curl -sf localhost:11434/api/tags >/dev/null || { echo "start the server: ollama serve" >&2; exit 1; }
ollama pull nomic-embed-text

mkdir -p "$OUT"
tar -xzf "$CACHE" -C "$OUT"
GATE_ARGS=""
for gate in $GATES; do GATE_ARGS="$GATE_ARGS --gate $gate"; done

run() {  # <name> <agent model>
  llm_cache="$OUT/.cache/llm"
  before=$(cat "$llm_cache"/*.jsonl | wc -l)
  # shellcheck disable=SC2086
  uv run thymus-eval --llm "$2" --judge ollama:qwen3:4b-instruct $GATE_ARGS --cache "$llm_cache" \
    --out "$OUT/$1" 2> "$OUT/$1.log" >/dev/null
  after=$(cat "$llm_cache"/*.jsonl | wc -l)
  echo "$1: $((after - before)) model calls not served by the cache"
}

case "$WHICH" in
  qwen) run qwen3-4b ollama:qwen3:4b-instruct ;;
  llama) run llama3.1-8b ollama:llama3.1:8b ;;
  *) run qwen3-4b ollama:qwen3:4b-instruct; run llama3.1-8b ollama:llama3.1:8b ;;
esac
DIRS=""
for d in "$OUT"/qwen3-4b "$OUT"/llama3.1-8b; do [ -d "$d" ] && DIRS="$DIRS $d"; done
# shellcheck disable=SC2086
uv run thymus-report $DIRS | tee "$OUT/report.md"
echo "Compare with paper/tables/full.tex (test split, same numbers)."
