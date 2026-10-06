# Plan: closing the gap completely

Written 6 October 2026, after re-checking every related-work claim against the papers.

## Two honest points first

- **No paper has zero future work.** Reviewers expect a limitations section, and a paper that
  claims to have solved everything loses trust. The achievable goal is different: **no
  objection a reviewer can raise that the paper has not already answered with data.** Every
  item below is chosen against a concrete objection.
- **Nobody can promise a best-paper award** (roughly 1–2% of accepted papers). We can build
  every part to the standard those papers share: one clear idea, a problem people feel,
  evidence that survives attack, and an artifact others use.

## How this paper differs from everything published

Each line of work answers a different question. Ours is the only one that asks the last:

| Line of work | Question it answers | Examples |
|---|---|---|
| Attacks and benchmarks | How do poisoned memories get in and get used? | MINJA, AgentPoison, MPBench, GhostWriter, MemPoison, PipePoison, Bad Memory |
| Store-or-block defences | Which memories should be refused or down-ranked? | MemGauge policies, Utility Under Attack, AM-Sentry, A-MemGuard |
| Labels for actions | How to stop untrusted memory from driving payments or data sends? | TMA-NM, PPMF |
| Cryptographic provenance | How to prove a memory was not forged? | SMSR |
| Revocation | Are outdated facts actually retired? | Revoked but Still Authoritative |
| **This paper** | **When a fact changes through an untrusted channel, how can the agent accept the real change, refuse the fake one shaped exactly like it, and answer honestly when it cannot tell?** | — |

What is new, stated precisely (and what is not):

1. **Matched real/fake update pairs.** No benchmark pairs each legitimate update with an
   attacker's twin on the same setup and question. Without the pair, a defence that blocks
   all updates looks perfect.
2. **Update semantics in the gate.** Same-origin supersession (only the user or the source
   that stated a fact may replace it) is not in any defence we found. The closest are
   revocation (who may retire a fact) and belief updating (how much to trust it).
3. **Labels for answers, not actions.** Keeping untrusted content with a label is **not** new
   (TMA-NM, PPMF). Using it to make the agent's *answers* disclose the source of contested
   facts, the case TMA-NM calls "mitigated, not eliminated", is.
4. **India and three languages**, with real scam patterns (UPI, KYC, electricity, FASTag).

## Claims audit (6 October 2026)

Checked against each paper's abstract or full text. Corrected:

- A-MemGuard is an arXiv preprint (Sep 2025), not "ICML 2026".
- Utility Under Attack does not say it "did not evaluate quarantine or delayed trust"; it
  tests only screening and provenance ranking, and says of bounded occupancy: "We have not
  implemented or evaluated such a gate".
- The draft said current defences only store or block. TMA-NM and PPMF keep and label
  untrusted content (for actions); the draft now says so.
- The draft claimed "disclosing beats hiding" and "frontier models resist poison far better"
  before having data. The first is now a placeholder; the second is false (Opus 5.5 adopts
  58% without a gate) and was removed.

Confirmed: all Utility Under Attack numbers, all MemGauge claims (systems, MINJA vs Sleeper,
62%, 50% admission, NC policy, SC upper bound), TMA-NM (0/1,920 pooled, 8 models, answer bias
quote), belief-based memory, Revoked (5 systems, 9 models), A-MemGuard (>95%), OWASP ASI06 =
"Memory and Context Poisoning".

Rule from now on: every number about another paper carries the exact quote in
`docs/related-work.md`; every number about ours comes from `thymus-report` output saved with
the commit that produced it.

## Findings that change the framing

- **6 Oct: on frontier models, labels alone did as well as the full gate.** On the
  36-scenario subset, label-only and thymus both give 8% attack success and 100% update and
  recall accuracy, for Opus 5.5 and GPT-6-Astra. Disclosure is the active ingredient there,
  which supports the title. What the screening and update rules add must be shown where
  labels alone are weak: adaptive attacks (flooding, label smuggling, relays), smaller models
  that ignore labels, and model-independent guarantees (`tests/test_invariants.py`). If the
  rules add nothing measurable anywhere, the paper says so and leads with disclosure plus the
  benchmark; it must not claim the rules help without data.

- **6 Oct: on Llama 3.1 8B, version 1 of the gate failed.** Attack success 48% vs 42% with
  no defence (old grader), flags only 8%: Llama ignores inline labels and answers with "the
  most recent memory". Without sender authentication, same-origin replacement also let
  forged senders replace real facts (spoofed-origin 59% vs 9% with no defence). Updates
  stayed high (92%; cross-origin 98%) and provenance quarantine again lost most updates (33%).
- **Response: thymus-v2** (commit d6d15de). (1) A source replaces its own fact only through
  an authenticated channel; a forged sender is kept as contested. (2) Contested claims are
  withheld from the model and disclosed in a system-written notice, so disclosure no longer
  depends on the model. (3) A user's claim that contradicts another user is contested.
  v1 results are kept and reported. **Because v2 was designed after seeing test-split results
  on Llama, its main evidence must come from data it was not designed on:** LongMemEval
  (Utility Under Attack protocol), the real SMS set, and the frontier models. The paper says
  this plainly. The cost to report: a real cross-origin update under v2 reaches the user as an
  unconfirmed notice instead of as the answer (`update_in_notice`).

## What to add, ranked

### Tier 1: answers the objections every reviewer will raise

| # | Addition | Objection it answers | Cost | Status |
|---|---|---|---|---|
| 1 | **Label-only baseline** (keep everything, label untrusted, no update rules): TMA-NM's idea applied to answers | "Isn't this just TMA-NM's labels?" | Small | Next |
| 2 | **Machine-checked invariants**: randomised property tests that the gate never lets tool content replace another origin's fact, never lets tool content speak for the user, never shows an untrusted memory without its source | "What does the gate guarantee, beyond averages?" | Small | Next |
| 3 | **Authenticated origins**: run with and without sender authentication (DKIM for email, registered SMS sender IDs, signed calendar invites) | "Spoofed origins break same-origin supersession" | Medium | Planned |
| 4 | **Automated adaptive attacker**: an attacker model that knows the gate and rewrites attacks over several rounds; plus the structural argument that content cannot remove a label or forge an origin | "Your adaptive attacks were hand-written" / PipePoison | Medium | Planned |
| 5 | **Blind grader validation**: 100 replies, you + a Claude helper + GPT, 4 labels, kappa | "Is the grader right?" (we already found one bug) | Your ~2 h | Tooling ready |
| 6 | **More model families**: Gemini (free CLI), Gemma and a larger Qwen on Kaggle | "Only four models" | Small | Gemini needs your login |
| 7 | **Comparability**: LongMemEval knowledge-update questions with the Utility Under Attack poisoning protocol | "Not comparable with prior numbers" | Medium | Planned |

### Tier 2: makes it stand out

| # | Addition | Why | Status |
|---|---|---|---|
| 8 | **Inside a real memory library (Mem0)** | TMA-NM already ran inside Mem0; parity | Planned |
| 9 | **Confirmation burden**: how often the user would be asked, if unverified facts are promoted by user confirmation or an independent origin | The cost nobody reports | Planned |
| 10 | **Real scam texts** from public datasets (licence permitting) for the attack side | "Scenarios are author-written" | Planned |
| 11 | **Long memory**: 80 background facts per scenario | Retrieval competition | Built |
| 12 | **Cost and latency** per write | Deployability | Planned |
| 13 | **User study**: do people act on the fake claim when the answer discloses it? | Turns "the model disclosed" into "the user was protected". Needs ethics approval, so needs a faculty mentor | Optional |

### Tier 3: impact

Open-source package and dataset, a leaderboard others can submit defences to, a guide for
Indian developers, and a contribution to OWASP's ASI06 guidance.

## Google's model

Google says Gemini 4 Argon (30 Sep 2026) is its "most resilient model yet against indirect
prompt injections", leading Gray Swan's IPI benchmark. That claim is about prompt injection,
not memory, and Argon is only for AI Ultra and paid API users, so we cannot test it for free.
We can test the strongest Gemini the free Gemini CLI login allows, through the same harness.
If memory-borne fake updates still work on it, that is exactly the point of the paper: robust
prompt-injection training does not stop a model from believing its own memory.
