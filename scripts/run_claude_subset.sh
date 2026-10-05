#!/bin/sh
# Strong-model check: Claude Sonnet as the agent on 12 balanced families (36 scenarios),
# run through the Claude Code CLI on a Claude subscription (no API key).
#   update sources: same-origin 4, user 4, cross-origin 4
#   attacks: lookalike 3, spoofed 3, other-user 2, other-channel 2, instruction 2
# Capped at 400 new calls; the response cache makes a rerun resume where it stopped
# (for example after the plan's usage limit resets).
set -eu
cd "$(dirname "$0")/.."

FAMILIES="standup-time apollo-deadline manager-name offsite-venue performance-review library-due-date
return-pickup pharmacy-refill family-trip-city flight-gate sip-date credit-card-due"

ONLY=""
for family in $FAMILIES; do
  ONLY="$ONLY --only $family--"
done

# Grading stays local (hybrid: keywords plus qwen3:4b-instruct) so the subscription is spent
# only on the agent.
# shellcheck disable=SC2086
uv run thymus-eval --llm claude-code:sonnet --judge ollama:qwen3:4b-instruct \
  --gate allow-all --gate user-only --gate thymus \
  --max-new-calls 400 --out results/claude-subset $ONLY
