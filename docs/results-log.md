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
