# Related work and where this project fits

First written 5 October 2026; every claim below was re-checked against the papers on
6 October 2026 (abstract or full text). Memory poisoning is a crowded area: at least 17 arXiv
papers on agent-memory attacks or defences in 2026 alone (listed at the end). The papers below
are the ones that decide what is still open.

## The closest papers

| Paper | What they did | Key result | What they left open |
|---|---|---|---|
| **Utility Under Attack** (Karunanidhi, Aug 2026) [2608.21230](https://arxiv.org/abs/2608.21230) | Poisoned 1.2% of LongMemEval with plain false facts (no instructions); tested a 4-stage write-time content screen and provenance-weighted retrieval | Accuracy 0.850 → 0.300. The screen rejects **0 of 360** poisoned memories. The shipped provenance weight is indistinguishable from no defence (p=0.80), and when the answer-bearing evidence arrives untrusted, a weight strong enough to resist poison drops accuracy to **0.0417** | Tests only those two defences (no quarantine, delayed trust or corroboration). Proposes "bounded occupancy" (reserve space for untrusted content in retrieval) and says: "We have not implemented or evaluated such a gate" |
| **MemGauge: Stage-Wise Utility-Risk Trade-offs** (Zang et al., Aug 2026) [2608.30177](https://arxiv.org/abs/2608.30177) | Varies write admission, management policy and retrieval exposure across Mem0, A-MEM, LangMem and Hindsight, on 11 LLMs, with MINJA and sleeper attacks | Attack success jumps once more than ~50% of content is written. Provenance quarantine stops sleeper (tool) attacks but **not MINJA**. Management policies cut attack success by up to 62% with little clean-utility loss | Its Numeric-Conflict policy (NC) "quarantines a newly written record when its numerical content conflicts with an existing trusted record", which would also block legitimate numeric updates; we found no separate report of knowledge-update questions. Its Strict Conflict policy "serves as an upper bound" (assumes complete, reliable feedback) |
| **TMA-NM: Origin-Bound Authority** (Louck, Jun 2026) [2606.24322](https://arxiv.org/abs/2606.24322) | Untrusted-origin content is stored but non-actionable, and the label propagates through summaries and tool echoes; a consequential action driven by untrusted content needs ≥2 independent trusted principals or fresh user authorisation | 0/1,920 pooled over laundering channels; 0/4,032 in the cross-model study; 100% legit utility (95.9% task utility cross-model), 8 frontier models; also holds at 0% inside Mem0 | States "Answer-bias is mitigated, not eliminated … TMA-NM guards the retrieval-to-action path, not free-text answers". Legitimate *updates* arriving untrusted are not a studied case |
| **Belief-Based Memory (Nous)** (Singh, Jun 2026) [2606.22030](https://arxiv.org/abs/2606.22030) | Bayesian belief updating with reliability estimates and provenance caps | Little gain over last-write-wins on standard benchmarks; helps when sources differ in trust; resists volumetric poisoning | No quarantine, delayed trust or user confirmation. Tested on LoCoMo plus synthetic contradictions |
| **Revoked but Still Authoritative** (Shen et al., Sep 2026) [2609.08258](https://arxiv.org/abs/2609.08258) | Five memory systems, nine models: are outdated ("revoked") facts actually suppressed? | No system enforces revocation by default; the revoked fact often outranks its replacement | Shows the update side is broken even without an attacker |
| **A-MemGuard** (Wei et al., arXiv Sep 2025) [2510.02373](https://arxiv.org/abs/2510.02373) | Consensus across reasoning paths from different memories, plus a "lessons" memory of past failures | Cuts attack success by more than 95% with small utility cost | Consensus can be faked by repetition (Louck's "manufactured corroboration") |

## Newer papers (found 6 October 2026) and why they don't close the gap

| Paper | What it does | Updates vs poison? |
|---|---|---|
| **MPBench** (Dash et al., Jun 2026) [2606.04329](https://arxiv.org/abs/2606.04329) | 4 write channels, 9 structural weaknesses, 6 attack classes; "existing prompt injection defenses fail to cover memory poisoning" | Not studied |
| **GhostWriter / AM-Sentry** (Torres et al., Jul 2026) [2607.06595](https://arxiv.org/abs/2607.06595) | Attack: ~98% injection, ~60% activation. Defence: a memory-saving policy plus a retrieval screen | Not studied |
| **MemPoison** (Gao et al., Jul 2026) [2607.14651](https://arxiv.org/abs/2607.14651) | 1,227 hand-validated cases, 10 model families; argues for adaptive, context-sensitive defences over static write-time filters | Not studied |
| **Bad Memory** (Gadgil et al., Jul 2026) [2607.14611](https://arxiv.org/abs/2607.14611) | Memory files of Claude Code and Codex: agents rarely overwrite memory from untrusted content, but already-planted payloads attack later sessions | Not studied |
| **PPMF: memory provenance laundering** (Xu et al., Jul 2026) [2607.29167](https://arxiv.org/abs/2607.29167) | Keeps platform provenance and authorises tool calls by the authority of the memories behind them | Actions only |
| **SMSR** (Sharma, Jun 2026) [2606.12703](https://arxiv.org/abs/2606.12703) | HMAC provenance plus randomised ablation with a certificate; end-to-end attack success 65.3% → 5.3%, clean utility 85–90% | Not studied |
| **PipePoison** (Zang et al., Sep 2026) [2609.00523](https://arxiv.org/abs/2609.00523) | Optimised end-to-end poisoning; stays effective under 8 representative defences | Attack only; a stress test for us |
| **LTM security survey** (Lin et al., Apr/Sep 2026) [2604.16548](https://arxiv.org/abs/2604.16548) | Security "must be anchored in storage-time provenance, versioning, and policy-aware retention" | Names the direction, no mechanism |

Others seen: MemAudit (2605.23723, post-hoc auditing), forensic trajectory signatures
(2606.30566), memory poisoning attack and defence (2601.05504), SuperLocalMemory
(2603.02240, Bayesian trust).

## What is already done (don't claim it)

- Measuring safety and usefulness together (MemGauge, Utility Under Attack).
- Provenance quarantine, and the finding that it fails against MINJA (MemGauge).
- Storing untrusted content with a label instead of blocking it, **to gate actions** (TMA-NM,
  PPMF). So "keep it but label it" alone is not new; using it for answers and updates is.
- Cryptographic provenance for memory writes (SMSR).
- Showing that content filters can't catch plain false facts (Utility Under Attack), and that
  optimised attacks beat many defences (PipePoison).

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
