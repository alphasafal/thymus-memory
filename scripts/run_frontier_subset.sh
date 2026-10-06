#!/bin/sh
# Frontier-model check: a subscription model as the agent on 12 balanced families
# (36 scenarios), run through its own CLI so no paid API key is needed.
#   update sources: same-origin 4, user 4, cross-origin 4
#   attacks: lookalike 3, spoofed 3, other-user 2, other-channel 2, instruction 2
#
# Usage: scripts/run_frontier_subset.sh <agent-model> [max-new-calls]
#   scripts/run_frontier_subset.sh claude-code:claude-opus-5-5 400   # Claude Pro plan
#   scripts/run_frontier_subset.sh codex:gpt-6-astra 400             # ChatGPT Plus plan
#
# Calls are capped, and the response cache makes a rerun resume where it stopped
# (for example after the plan's usage limit resets). The cache lives in its own folder so
# this can run next to the main experiment without two processes writing one cache file.
set -eu
cd "$(dirname "$0")/.."

AGENT="$1"
MAX_CALLS="${2:-400}"
OUT="results/frontier-$(echo "$AGENT" | tr ':/' '__')"

FAMILIES="standup-time apollo-deadline manager-name offsite-venue performance-review library-due-date
return-pickup pharmacy-refill family-trip-city flight-gate sip-date credit-card-due"

ONLY=""
for family in $FAMILIES; do
  ONLY="$ONLY --only $family--"
done

# Gates to run; override with e.g. GATES="label-only" scripts/run_frontier_subset.sh ...
GATE_ARGS=""
for gate in ${GATES:-allow-all user-only thymus}; do
  GATE_ARGS="$GATE_ARGS --gate $gate"
done

# Grading stays local (hybrid: keywords plus qwen3:4b-instruct) so the plan is spent only
# on the agent.
# shellcheck disable=SC2086
uv run thymus-eval --llm "$AGENT" --judge ollama:qwen3:4b-instruct $GATE_ARGS \
  --cache .cache/frontier --max-new-calls "$MAX_CALLS" --out "$OUT" $ONLY
