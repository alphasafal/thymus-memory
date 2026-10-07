# Results log

Snapshots as runs finish. Test split unless noted; regenerate any table with `thymus-report`.

## 6 Oct 2026: qwen3:4b-instruct, all defences (Kaggle, fixed grader), 442 test scenarios

| Defence | Fooled ↓ | Real updates ↑ | Recall ↑ |
|---|---|---|---|
| allow-all | 38% | 95% | 98% |
| user-only (provenance quarantine) | 14% | 30% | 25% |
| conflict-quarantine | 32% | 81% | 98% |
| last-write-wins | 44% | 95% | 98% |
| bounded-occupancy | 22% | 56% | 97% |
| label-only | 17% | 94% | 98% |
| thymus (v1) | 17% | 94% | 96% |
| thymus-v2-inline | 16% | 94% | 96% |
| **thymus-v2** | **8%** | 69% answered + 25% disclosed in the notice (94% reach the user) | 96% |
| ablation: no labels | 38% | 95% | 96% |
| ablation: hide contested | 10% | 69% (30% stale) | 96% |

v2 updates (142): 98 answered; 35 cross-origin updates reached the user only as an
unconfirmed notice; 9 missed.

## 6 Oct 2026: frontier models, 36-scenario subset (+16 adaptive for GPT)

Keyword grading for v2 rows (full regrade pending); keyword grading is the stricter one.

| Model · defence | Fooled | Real updates |
|---|---|---|
| Opus 5.5 · allow-all | 58% | 100% |
| Opus 5.5 · user-only | 17% | 33% |
| Opus 5.5 · label-only / thymus | 8% | 100% |
| Opus 5.5 · thymus-v2 / v2-inline | 0% / 0% | 67% / 100% |
| GPT-6-Astra · allow-all | 50% (44% on adaptive) | 100% |
| GPT-6-Astra · label-only / thymus | 4% (incl. adaptive) | 100% |
| GPT-6-Astra · thymus-v2 / v2-inline | 0% / 0% | 67% / 100% |

## 6 Oct 2026: Llama 3.1 8B (old grader, regrade running on Kaggle)

allow-all 42% fooled; thymus v1 48% fooled with 8% flagged (Llama ignores inline labels);
spoofed-origin 59% under v1 vs 9% with no defence. v2 results pending.

## Reading

- Disclosure is the active ingredient. Whether it can be left to the model depends on the
  model: frontier models and qwen3 follow inline labels, Llama 3.1 8B does not.
- v2's system notice makes disclosure model-independent: lowest attack success on every
  model so far, at the cost of cross-origin updates arriving as notices instead of answers.
- With a model that follows labels, v2-inline gets both: 0% attacks and 100% updates on
  Opus 5.5 and GPT-6-Astra.

## 6 Oct 2026: Llama 3.1 8B, all defences and ablations (Kaggle, fixed grader), 442 test scenarios

| Defence | Fooled ↓ | Real updates ↑ | Recall ↑ |
|---|---|---|---|
| allow-all | 42% | 91% | 94% |
| user-only | 17% | 33% | 28% |
| conflict-quarantine | 30% | 78% | 94% |
| last-write-wins | 78% | 94% | 94% |
| bounded-occupancy | 31% | 54% | 84% |
| label-only | 41% | 91% | 95% |
| thymus (v1) | 47% | 92% | 94% |
| thymus-v2-inline | 44% | 92% | 94% |
| **thymus-v2** | **20%** (67% flagged) | 81% + notices | 94% |
| ablation: hide contested | 28% | 81% | 94% |

Inline disclosure does nothing for a model that ignores labels; the system notice halves
attack success and beats hiding. Ablations under v1: no labels 63%, any-origin 64%.

## 6 Oct 2026: real smishing SMS (Mishra & Soni 2022), frontier models, keyword grading

| Model · defence | Passes the scam on as genuine |
|---|---|
| Opus 5.5 (79 India SMS) · allow-all | 41% |
| Opus 5.5 · label-only / thymus-v2 | 22% / 22% |
| GPT-6-Astra (117 SMS) · all defences | 0%: its extraction stored nothing from 116 of 117 scam messages |

## 6 Oct 2026: LongMemEval_S, Utility Under Attack protocol, Llama 3.1 8B (agent and gate), qwen3 grader

| Condition | Defence | Accuracy ↑ | Adopts false answer ↓ | Flags it |
|---|---|---|---|---|
| clean | allow-all / label-only | 63% / 63% | – | – |
| clean | thymus-v2 | **26%** | – | – |
| poisoned | allow-all | 24% | 63% | 0% |
| poisoned | user-only / conflict-quarantine | 63% / 63% | 5% / 6% | 0% |
| poisoned | label-only | 29% | 53% | 0% |
| poisoned | bounded-occupancy | 34% | 54% | 0% |
| poisoned | thymus-v2 / v2-inline | 23% / 18% | 37% / 57% | 50% / 2% |
| evidence-untrusted | allow-all | 24% | 63% | 0% |
| evidence-untrusted | user-only / conflict-quarantine | **11%** / 13% | 2% / 4% | – |
| evidence-untrusted | label-only / bounded-occupancy | 28% / 5% | 56% / 75% | – |
| evidence-untrusted | thymus-v2 | 16% | 35% | 52% |

Reading: (1) reproduces Utility Under Attack's finding that provenance blocking collapses
when real answers arrive untrusted (63% → 11%; they report 0.0417). (2) **Negative result
for thymus-v2 on long real chats:** clean accuracy 63% → 26%. Memories here are whole chat
rounds holding many facts; replacing a round because one fact changed deletes unrelated
facts, and an 8B gate model over-detects conflicts. Fix under test: soft replacement (keep
older versions, labelled), never deleting multi-fact memories.

## 6 Oct 2026: real smishing SMS, open models (117 messages)

| Model | allow-all | user-only | label-only | thymus (all variants) |
|---|---|---|---|---|
| Llama 3.1 8B: passes the scam on | 70% | 0% | 31% | **25%** |
| qwen3-4B | 9% | 0% | 1% | 1% |

## 7 Oct 2026: soft replacement (thymus-v2-soft), Llama 3.1 8B, Kaggle

LongMemEval_S (UUA protocol, same 120 questions and poison as above):

| Condition | allow-all | user-only | thymus-v2 | **thymus-v2-soft** |
|---|---|---|---|---|
| clean: accuracy | 63% | – | 26% | **62%** |
| poisoned: accuracy / adopts / flags | 24% / 63% / 0% | 63% / 5% / 0% | 23% / 37% / 50% | **47% / 32% / 60%** |
| evidence-untrusted: accuracy / adopts | 24% / 63% | 11% / 2% | 16% / 35% | 12% / 53% |

Benchmark (491 scenarios, paired with thymus-v2 on the same scenarios and cached extractions):

| Gate | Attacks blocked | Updates correct | Stale answer | Recall |
|---|---|---|---|---|
| thymus-v2 | 143 / 178 | 127 / 157 | 16 | 148 / 156 |
| thymus-v2-soft | **168 / 178** | 104 / 157 | 48 | 148 / 156 |

Reading: keeping replaced memories restores clean utility on multi-fact memories (26% → 62%,
allow-all 63%) and doubles poisoned accuracy over allow-all (24% → 47%). On one-claim memories
it costs updates: the 8B model answers from the labelled older version (stale 16 → 48; 27 of
the 29 lost updates are cross-origin). The trade-off follows memory granularity, so
**thymus-v2-auto** retires replaced single claims and keeps multi-fact memories labelled; on
both suites it should reproduce the better column (running on Kaggle). Evidence-untrusted
stays hard for every defence: when the real answer itself arrives untrusted, nothing that
trusts provenance can recover it (UUA's point); v2 discloses instead of dropping (flags 38%).

## 7 Oct 2026: hybrid regrade of the keyword-graded frontier runs (Kaggle, qwen3 grader)

Frontier subset (Opus 5.5, GPT-6-Astra, GPT adaptive): every number unchanged (v2 and
v2-inline 0% fooled; v2 updates 67%, v2-inline 100%).

Real smishing, Opus 5.5 (79 India SMS): keyword grading overcounted, since it counted a reply
that names the scam's number *while warning against it* as relaying it.

| Defence | keyword | hybrid (reported) |
|---|---|---|
| allow-all | 41% | **19%** |
| label-only | 22% | **10%** |
| thymus-v2 | 22% | **10%** |

GPT-6-Astra real SMS: 0% under every defence (stored 1 of 117).

## 7 Oct 2026: thymus-v2-auto (granularity-aware replacement), Llama 3.1 8B, Kaggle

| Suite | thymus-v2 (hard) | thymus-v2-soft | **thymus-v2-auto** |
|---|---|---|---|
| LongMemEval clean: accuracy | 26% | 62% | **62%** |
| LongMemEval poisoned: accuracy / adopts / flags | 23% / 37% / 50% | 47% / 32% / 60% | **47% / 32% / 60%** |
| LongMemEval evidence-untrusted: accuracy / adopts | 16% / 35% | 12% / 53% | 12% / 53% |
| Benchmark test split: fooled / updates / recall | 20% / 81% / 94% | – | **20% / 78% / 94%** |
| Benchmark all 491, paired: attacks blocked / updates / recall | 143 / 127 / 148 | 168 / 104 / 148 | 144 / 123 / 148 |

Auto matches soft on multi-fact memories and hard on single claims (paired: 1 attack more
blocked, 4 updates fewer than hard, of 178 / 157). It is the final gate.

## 7 Oct 2026: real email (Kaggle, hybrid qwen3 grader)

**Enron real updates, matched by provenance** (31 real update pairs; each real update also
replayed from a lookalike sender and from a forged sender; 93 scenarios):

| Model · defence | Fooled by replayed update ↓ (lookalike / forged) | Real updates correct ↑ |
|---|---|---|
| Llama 8B · allow-all | 84% (87% / 81%) | 71% |
| Llama 8B · user-only | 0% | **0%** |
| Llama 8B · label-only | 87% | 77% |
| Llama 8B · thymus v1 | 87% | 87% |
| Llama 8B · **thymus-v2** | **3%** (3% / 3%) | **87%** |
| qwen3-4B · allow-all | 76% (77% / 74%) | 74% |
| qwen3-4B · user-only | 0% | **0%** |
| qwen3-4B · label-only | 50% | 74% |
| qwen3-4B · **thymus-v2** | **18%** (16% / 19%) | **74%** |

**Nazario phishing email** (112 real emails, redacted):

| Model | allow-all | user-only | label-only | thymus / v2 |
|---|---|---|---|---|
| Llama 8B: relays the phish | 48% | 0% | 29% | 30% |
| qwen3-4B | 29% | 0% | 8% | 10% |

Reading: on real email the store-or-block dilemma is total: provenance quarantine keeps
0% of real updates, no defence is fooled by 76–84% of replayed ones. v2 keeps every real
update the undefended agent gets (more: it retires the old value) and is fooled by 3–18%.
Single phishing messages contradict nothing, so v2 = v1 there; the gain comes from
screening and labels, and Llama again ignores labels.

## 7 Oct 2026: gate model ≠ agent model (Llama 3.1 8B agent, qwen3-4B gate), Kaggle, test split

| Language | Fooled: Llama gate → qwen3 gate | Paired (exact McNemar) | Updates: Llama gate → qwen3 gate |
|---|---|---|---|
| English | 17% → 22% | 14 vs 9 discordant, p = 0.41 | 82% → 71% (p = 0.08) |
| Hindi | 23% → 13% | 3 vs 6, p = 0.51 | 73% → 67% |
| Hinglish | 27% → **3%** | 0 vs 7, **p = 0.016** | 87% → 83% |

Overall: 17% fooled, 73% updates, 92% recall (Llama's own gate: 20%, 81%, 94%). v2 and
v2-auto identical here (single-claim memories). Reading: the gate's judgments, not its
rules, carry the language gap; a different 4B gate model removes Hinglish attacks almost
entirely without costing updates, helps Hindi (not significant at n = 30), and is no
better in English. Picking the gate model per language, or a stronger one, is the lever.

## 7 Oct 2026: GPT-6-Astra on real Enron updates (15 pairs = 45 scenarios, ChatGPT plan, keyword grading)

| Defence | Fooled by the replay (lookalike / forged) | Real updates |
|---|---|---|
| allow-all | 80% (80% / 80%) | 80% |
| user-only | 0% | **0%** |
| **thymus-v2-auto** | **0%** (80% of attacks disclosed) | **80%** |

The gate keeps every real update the undefended frontier agent gets and adopts none of the
replays. Keyword grading counts any mention of the new value as adoption, so the 0% is not
flattered; allow-all may be slightly overstated (hybrid regrade pending).

## 7 Oct 2026: multilingual gate model (Aya Expanse 8B) for a Llama agent, test split

| Fooled ↓ / updates ↑ | Llama gate | qwen3-4B gate | Aya Expanse 8B gate |
|---|---|---|---|
| English | 17% / 82% | 22% / 71% | 19% / 74% |
| Hindi | 23% / 73% | 13% / 67% | 17% / 70% |
| Hinglish | 27% / 87% | **3%** / 83% | 20% / 80% |

No Aya difference from Llama's own gate is significant (exact McNemar, all p > 0.1).
Overall Aya: 19% fooled, 75% updates, 96% recall. Reading: a model marketed as multilingual
does not by itself close the gap; only qwen3 on Hinglish does (p = 0.016). Hindi stays at
13–23% with every small gate model tried: an open problem, reported as such.

## 7 Oct 2026: Claude Opus 5.5 on real Enron updates (8 pairs = 24 scenarios, Claude plan, keyword grading)

| Defence | Fooled by the replay (lookalike / forged) | Real updates |
|---|---|---|
| allow-all | 56% (62% / 50%) | 62% |
| user-only | 0% | **0%** |
| **thymus-v2-auto** | **12%** (0% / 25%) | **62%** |

Both v2-auto failures are forged-sender replays answered with the forged value *plus* "I
haven't been able to confirm this": a caveat, which strict scoring counts as fooled. In one,
the forged email yielded several facts and only some were linked to the original; in the
other the conflict was not detected, so the claim reached Opus as an unverified (labelled)
memory and Opus disclosed it rather than adopting it silently. ~72 agent runs, ≈200 Opus calls.

## 7 Oct 2026: long memory (80 background facts per scenario), qwen3-4B, Kaggle, test split

| Defence | Fooled ↓ | Updates: answered / reach the user* | Recall: answered / reach the user* |
|---|---|---|---|
| allow-all | 28% | 80% / 80% | 91% / 91% |
| user-only | 13% | 29% / 29% | 24% / 24% |
| bounded-occupancy | 16% | 48% / 48% | 87% / 87% |
| label-only | 23% | 84% / 84% | 92% / 92% |
| thymus-v2 / v2-auto | **14%** (6% lenient) | 63% / **85%** | 76% / **90%** |

*answered, or disclosed in the system notice. Reading: in a big store the 4B conflict
detector raises false contradictions between *similar* facts about *different* things ("car
service 26 Oct" vs a water-purifier service on 23 Oct); 20 of 35 recall misses are such false
contests. The fact is withheld from the answer but still reaches the user in the notice, so
v2 halves attacks while delivering as much as no defence, at a usability cost (14 points of
recall arrive as "unconfirmed"). Fix under test: a stricter same-subject conflict check.
