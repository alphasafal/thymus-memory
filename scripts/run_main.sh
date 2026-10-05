#!/bin/sh
# Main experiment: every defence on all 205 scenarios with a local agent model.
# Takes several hours on an 8 GB M2 Mac. Responses are cached in .cache/llm, so an
# interrupted run picks up where it stopped when started again.
#
# Usage: scripts/run_main.sh [agent-model] [grader]
#   scripts/run_main.sh ollama:qwen3:4b same
#   scripts/run_main.sh ollama:qwen3:4b claude-code
set -eu
cd "$(dirname "$0")/.."

AGENT="${1:-ollama:qwen3:4b}"
GRADER="${2:-same}"
OUT="results/main-$(echo "$AGENT" | tr ':/' '__')"

# caffeinate keeps the Mac awake for as long as the run lasts (macOS only).
if command -v caffeinate >/dev/null 2>&1; then
  KEEP_AWAKE="caffeinate -i"
else
  KEEP_AWAKE=""
fi

$KEEP_AWAKE uv run thymus-eval --llm "$AGENT" --judge "$GRADER" --out "$OUT"
