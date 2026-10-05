# Paper outline (working draft)

**Working title:** *Disclose, Don't Decide: Separating Real Updates from Poisoned Ones in LLM Agent Memory*

## One-sentence claim

Memory defences for LLM agents treat every new memory as a store-or-block decision, which
forces a trade between letting poison in and losing legitimate updates. Adding a third
outcome, keeping a claim but recalling it as unverified with its source, plus a rule that a
fact can be replaced only by the user or by the source that stated it, improves on that
trade-off on a matched-pair benchmark where store-or-block defences cannot.

## Contributions

1. **Matched-pair benchmark (205 scenarios).** 60 real-life fact families, each with a recall
   control, a legitimate update and an attacker's fake update that share the same setup, plus
   25 hand-written scenarios. The fake updates cover lookalike senders, other users of a
   shared assistant (MINJA-style), other channels, spoofed senders and instructions disguised
   as facts. Real updates come from the same source, the user, or a different source.
2. **Measurement that separates "adopted" from "flagged".** A reply that mentions a planted
   claim with a clear warning is scored separately from one that adopts it. Graders are
   validated against 58 hand-labelled replies, and grader accuracy is reported.
3. **Thymus gate.** Self/non-self screening (tool content cannot speak for the user),
   same-origin supersession, and disclosure of unverified claims at recall time.
4. **Head-to-head with prior-work defences** reimplemented in one harness: provenance
   quarantine and conflict quarantine (MemGauge), bounded occupancy (proposed in Utility Under
   Attack, unbuilt there), last-write-wins, and no defence.

## Research questions

- **RQ1.** How do existing defences trade attack success against legitimate-update accuracy?
- **RQ2.** Does the thymus gate move the trade-off (lower attack success *and* equal or higher
  update accuracy), or only move along it?
- **RQ3.** Where does it fail? Expected: cross-origin real updates and spoofed same-origin
  attacks. Quantify both.
- **RQ4.** Does disclosure work, i.e. do agents actually warn when shown an "unverified"
  label, and does that depend on model size?
- **RQ5.** How much do results depend on the agent model (3B vs 4B local, and Claude on a
  small subset)?

## Experiments

| Experiment | Models | Scenarios | Gates |
|---|---|---|---|
| Main table | qwen3:4b agent, best validated grader | all 205 | all 6 |
| Model sensitivity | qwen2.5:3b, qwen3:4b; Claude subset via subscription | 60 families | allow-all, user-only, thymus |
| Ablations | qwen3:4b | all 205 | thymus without disclosure; without same-origin rule; without claim classifier |
| Grader validation | each grader | 58 labelled replies | n/a |

Breakdowns: by attack kind, by update source, by domain; stored vs used (where attacks get in).

## Threats to validity (state them plainly)

- Small local models as agents; frontier models may behave differently.
- Scripted scenarios, not real user traffic. Families were written by the authors.
- Origins are assumed authentic except in the spoofed-origin cases; real systems need
  authenticated senders (DKIM, signed calendar invites).
- A model grader, even validated, has error; report its accuracy and keyword agreement.
- Single-turn probes; no long haystacks yet (bounded occupancy is designed for those).

## Related work to position against

See `docs/related-work.md`: Utility Under Attack (2608.21230), MemGauge (2608.30177), TMA-NM
(2606.24322), belief-based memory (2606.22030), revocation study (2609.08258), A-MemGuard,
MINJA, AgentPoison, MemoryAgentBench.
