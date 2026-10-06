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
