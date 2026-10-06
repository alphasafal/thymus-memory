#!/bin/sh
# Ablations: the full thymus gate against versions with one part switched off
# (screening, same-origin rule, labels, disclose-instead-of-hide), on every scenario.
# Thymus itself is included so the comparison is paired; with the shared response cache
# its runs come free if the main experiment already ran with the same agent model.
#
# Usage: scripts/run_ablations.sh [agent-model] [grader]
set -eu
cd "$(dirname "$0")/.."

AGENT="${1:-ollama:qwen3:4b-instruct}"
GRADER="${2:-same}"
OUT="results/ablations-$(echo "$AGENT" | tr ':/' '__')"

if command -v caffeinate >/dev/null 2>&1; then
  KEEP_AWAKE="caffeinate -i"
else
  KEEP_AWAKE=""
fi

$KEEP_AWAKE uv run thymus-eval --llm "$AGENT" --judge "$GRADER" --out "$OUT" \
  --gate thymus --gate thymus-no-screen --gate thymus-any-origin --gate thymus-no-labels --gate thymus-hide
