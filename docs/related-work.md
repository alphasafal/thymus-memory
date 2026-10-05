# Related work and where this project fits

Checked on 5 October 2026. Memory poisoning is a crowded area: more than 15 papers in 2026 alone.
The papers below are the ones that decide what is still open.

## The closest papers

| Paper | What they did | Key result | What they left open |
|---|---|---|---|
| **Utility Under Attack** (Karunanidhi, Aug 2026) [2608.21230](https://arxiv.org/abs/2608.21230) | Poisoned 1.2% of LongMemEval with plain false facts (no instructions); tested a 4-stage write-time content screen and provenance-weighted retrieval | Accuracy 0.85 → 0.30. The screen caught **0 of 360** poisoned memories. Provenance weighting either does nothing (p=0.80) or excludes all untrusted content, and when real answers arrive untrusted, accuracy falls to **0.04** | Says it did **not** evaluate quarantine, delayed trust, corroboration or write-time gating with provenance. Proposes "bounded occupancy" (cap the untrusted share of retrieved context) but did not build it. Attacker is non-adaptive |
| **MemGauge: Stage-Wise Utility-Risk Trade-offs** (Zang et al., Aug 2026) [2608.30177](https://arxiv.org/abs/2608.30177) | Varies write admission, management policy and retrieval exposure across Mem0, A-MEM, LangMem and Hindsight, on 11 LLMs, with MINJA and sleeper attacks | Attack success jumps once more than ~50% of content is written. Provenance quarantine stops sleeper (tool) attacks but **not MINJA**. Management policies cut attack success by up to 62% with little clean-utility loss | Its conflict policy quarantines new records that conflict with trusted ones, which would also block legitimate updates; knowledge-update questions are not reported separately. Its verification policy is an idealised upper bound, not a real mechanism |
| **TMA-NM: Origin-Bound Authority** (Louck, Jun 2026) [2606.24322](https://arxiv.org/abs/2606.24322) | Untrusted content is stored but marked non-actionable; the label survives summarisation; actions need independent trusted corroboration or user confirmation | **0 of 1,920** attacks succeed on consequential actions (payments, data sends), with 96–100% legitimate utility, across 8 frontier models | Explicitly out of scope: **"answer biasing"**, false facts that corrupt answers rather than trigger actions ("mitigated, not eliminated") |
| **Belief-Based Memory (Nous)** (Singh, Jun 2026) [2606.22030](https://arxiv.org/abs/2606.22030) | Bayesian belief updating with reliability estimates and provenance caps | Little gain over last-write-wins on standard benchmarks; helps when sources differ in trust; resists volumetric poisoning | No quarantine, delayed trust or user confirmation. Tested on LoCoMo plus synthetic contradictions |
| **Revoked but Still Authoritative** (Shen et al., Sep 2026) [2609.08258](https://arxiv.org/abs/2609.08258) | Five memory systems, nine models: are outdated ("revoked") facts actually suppressed? | No system enforces revocation by default; the revoked fact often outranks its replacement | Shows the update side is broken even without an attacker |
| **A-MemGuard** (ICML 2026) [2510.02373](https://arxiv.org/abs/2510.02373) | Consensus across reasoning paths from different memories, plus a "lessons" memory of past failures | Cuts attack success by more than 95% with small utility cost | Consensus can be faked by repetition (Louck's "manufactured corroboration") |

## What is already done (don't claim it)

- Measuring safety and usefulness together (MemGauge, Utility Under Attack).
- Provenance quarantine, and the finding that it fails against MINJA (MemGauge).
- Stopping poisoned memories from triggering **actions** (TMA-NM).
- Showing that content filters can't catch plain false facts (Utility Under Attack).

## What is still open

1. **Legitimate updates arriving through untrusted channels.** A real "your delivery is delayed" email
   and a fake "your order was cancelled" email look the same to a gate. No paper measures this
   pairing directly. Conflict-quarantine policies would block both.
2. **Delayed trust or maturation as a real mechanism.** Listed as unevaluated by Utility Under Attack;
   only an idealised upper bound in MemGauge.
3. **False facts in answers.** TMA-NM explicitly leaves these open.
4. **Bounded occupancy.** Proposed by Utility Under Attack but never built or tested.

## This project's question

> Can a memory agent accept legitimate fact updates that arrive through untrusted channels while
> rejecting false updates shaped exactly like them, without asking the user to confirm everything?

Planned contributions:

1. **Matched-pair benchmark.** Every legitimate update has a poisoned twin through the same channel
   (`calendar-standup-moved` vs `fake-update-standup`, `email-delivery-delayed` vs
   `fake-update-order-cancelled`, `user-new-manager` vs `fake-update-manager`). Grow from 3 pairs to
   ~100, and add LongMemEval's 78 knowledge-update questions with the Utility Under Attack poisoning
   protocol so results compare with prior work.
2. **Thymus gate.** Untrusted updates enter quarantine. A quarantined update is used with a stated
   caveat ("an email from X says..., unconfirmed"), and is promoted only after corroboration from
   an independent origin or user confirmation. Versioning makes sure the old value is actually retired.
3. **Baselines from prior work:** allow-all, user-only (≈ MemGauge provenance quarantine),
   conflict-quarantine (≈ MemGauge numeric-conflict policy), last-write-wins, and bounded occupancy.
4. **A cost metric no one reports:** confirmation burden, meaning how often the user must be asked.

## Risks

- The area moves fast; someone may publish this angle soon. Post early (arXiv or a workshop).
- TMA-NM's corroboration-plus-confirmation is close to our maturation idea. The difference must stay
  clear: facts and updates in answers, not consequential actions.
- Corroboration can be manufactured (the `repeated-product-push` scenario). The gate must require
  independent origins, not just repeated text.
