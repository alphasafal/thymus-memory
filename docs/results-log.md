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

## 7 Oct 2026: thymus-v2-precise (same-subject conflict check), paired with v2-auto, test split

| Suite | Fooled: auto → precise | Updates answered | Recall answered |
|---|---|---|---|
| qwen3-4B, 80 background facts | 14% → 13% (p = 0.63) | 63% → 65% | 76% → **82%** (p = 0.022) |
| qwen3-4B, normal | 8% → 9% (p = 0.50) | 69% → 73% (p = 0.06) | 96% → 96% |
| Llama 3.1 8B, normal | 20% → 18% (p = 0.58) | 78% → 79% | 94% → 94% |

Telling the conflict detector that only facts about the same specific thing conflict
recovers 6 points of large-store recall with no loss of safety anywhere. Gap to no defence
(91%) remains; next: verify each claimed conflict pairwise.

## 7 Oct 2026: thymus-v2-verified (same-subject check + pairwise confirmation), test split

Fooled ↓ / updates answered (reach the user) / recall answered (reach the user):

| Suite | allow-all | v2-auto | v2-precise | **v2-verified** |
|---|---|---|---|---|
| qwen3-4B, 80 background facts | 28% / 80 / 91 | 14% / 63 (85) / 76 (90) | 13% / 65 / 82 | 18% / 75 (83) / **89** |
| qwen3-4B, normal | 38% / 95 / 98 | 8% / 69 (94) / 96 | 9% / 73 / 96 | 11% / **87** (94) / 96 |
| Llama 3.1 8B, normal | 42% / 91 / 94 | 20% / 78 (92) / 94 | 18% / 79 / 94 | **10%** / 63 (89) / 94 |

Paired vs v2-auto (exact McNemar): qwen3 large-store recall +13 pts (0 vs 19, p < 0.001),
qwen3 updates +18 pts (1 vs 26, p < 0.001), qwen3 attacks +3 pts (p = 0.07, n.s.); Llama
attacks −10 pts (19 vs 4 discordant, p = 0.003), Llama updates answered −15 pts (24 vs 3,
p < 0.001: 22 cross-origin updates now arrive as notices).
By language, fooled: Llama en 11%, hi **3%** (auto 23%), hinglish 13% (auto 23%); qwen3
en 8%, hi 20% (v2 13%), hinglish 13%.

Reading: confirming each claimed conflict on its own fixes the large-store recall loss and
returns most updates as answers on qwen3. On Llama the cleaner store leads the gate to
contest more real conflicts: safer (and Hindi attacks nearly vanish) but more updates come
as notices. In every suite 83–96% of the right information reaches the user. Final gate:
v2-verified; real-data and LongMemEval reruns queued.

## 12 Oct 2026: the first verifier wording drops real conflicts on real data (negative result)

Reruns with v2-verified (first wording), Kaggle, hybrid qwen3 grader:

| Suite | v2 / v2-auto | v2-verified, first wording |
|---|---|---|
| Enron replays, Llama: fooled / real updates | 3% / 87% | 13% / 81% |
| Enron replays, qwen3: fooled / real updates | 18% / 74% | 31% / 77% |
| Phishing relayed, Llama / qwen3 | 30% / 10% | 30% / 10% |
| SMS relayed, Llama / qwen3 | 25% / 1% | 25% / 1% |
| LongMemEval clean / poisoned acc. (adopts, flags) | 62% / 47% (32%, 60%) | 63% / 32% (48%, 8%) |
| LongMemEval evidence-untrusted acc. (adopts) | 12% (53%) | 13% (66%) |

Diagnosis from the cached verifier answers:
- Asked "same specific thing?" directly, small models read a changed detail as a different
  thing: "Meeting Tue Sep 11, 3-4 PM, EB3321" vs "The meeting is rescheduled for Sept 13 at
  3 PM in EB3321" → same_thing = false. qwen3 confirmed only 16 of 48 Enron conflicts.
- LongMemEval memories are whole chat rounds; the verifier confirmed 13% of claimed conflicts
  (607 of 4,706), so poisoned rounds went uncontested (flags 60% → 8%).

Fixes: (1) the verifier first names what each fact is about without its details, then
compares; (2) only single claims are verified pairwise; multi-fact memories keep the first
verdict (the same granularity rule as replacement).

Calibration round 1 (455 labelled pairs, real conflicts kept / non-conflicts kept):

| Pairs | qwen3 first → named-subject | Llama first → named-subject |
|---|---|---|
| benchmark real conflicts (241) | 91 → 188 | 235 → 167 |
| Enron real conflicts (45) | 20 → 38 | 41 → 36 |
| similar background pairs, not conflicts (120) | 0 → 5 | 68 → 5 |

The run-derived "haystack non-conflicts" (49) turned out to be mostly real conflicts: the
haystack put facts from overlapping families in the background (the standup-time family
behind the hand-written standup scenarios; electricity-bill behind electricity-bill-india;
"The EMI is ₹14,200" behind loan-emi). Background facts were also elliptical extracted
sentences ("The deadline is 30 November"). **Haystack bug, fixed**: background memories are
now each family's original message (which names its subject), and families about the same
thing (eval/haystack_related.json, X / X-india) never supply each other's background. The
earlier large-store numbers over-counted false contests for every defence; all haystack
runs are redone.

Calibration round 2 (clean labels, hard negatives from unrelated background messages, a
third wording that says a brand named in only one fact is not a different thing, split by
family: choose on half A, report on half B) is running; then every suite is rerun with the
chosen wording.

## 21 Oct 2026: frozen gate (thymus-v2-verified, named-subject verifier), test split

Verifier wording chosen on half A of 582 labelled pairs (paper Table `tab:verifier`), frozen
(tag `gate-frozen`), then every benchmark and real-data suite rerun on Kaggle.

| Suite | allow-all | v2-auto (no verification) | **final** | first wording (12 Oct) |
|---|---|---|---|---|
| qwen3-4B fooled / updates / recall | 38 / 95 / 98 | 8 / 69 / 96 | **9 / 76 (94 reach) / 96** | 11 / 87 / 96 |
| Llama 3.1 8B fooled / updates / recall | 42 / 91 / 94 | 20 / 78 / 94 | **25 / 72 (89 reach) / 94** | 10 / 63 / 94 |
| Enron replays fooled / real updates, qwen3 | | 18 / 74 | **24 / 77** | 31 / 77 |
| Enron replays fooled / real updates, Llama | | 3 / 87 | **18 / 77** | 13 / 81 |

**Negative result on Llama.** The final gate is no longer the safest defence there: user-only
17% (but 33% updates, 28% recall), v2-auto 20%, final 25% (McNemar vs v2-auto 21/29, p = 0.32).
Against the first wording, 29 attacks now get through and 3 no longer do. Cause: the
named-subject verifier keeps 76% of Llama's real conflicts (first wording: 97%); a conflict the
verifier refuses is not contested, so the fake update reaches Llama with only an inline label,
which Llama ignores (§ v1 → v2). 45 of 45 successful attacks were stored; 6 carried a notice.

Lesson for the design: the verifier is a security component with asymmetric errors. A false
contest costs a notice; a missed conflict costs an attack. Choosing the wording by counting
both errors equally on half A was the wrong criterion for Llama.

Also fixed: paper_numbers.py looked for update kind "cross-origin" (the kind is
"cross-origin-update"), so the cross-origin macros were empty.

## 21 Oct 2026: frontier subset with v3 (held-out for v3), GPT-6-Astra

36 scenarios (12 families). v3 and v2-verified identical: fooled 0% (allow-all 50% earlier),
recall 100%, updates answered 8/12; the 4 not answered are all cross-origin updates, and all 4
reach the user in the notice (12/12 reach). Opus 5.5 rerun blocked by the Claude plan's weekly
limit (resets 24 Oct 02:30 IST); its v3 rows are errors until rerun.

Opus 5.5 rerun on a second Claude account (21 Oct): v3 and v2-verified identical, fooled 0/12
(allow-all 58%, label-only 8%, thymus v1 8%), recall 12/12, updates answered 8/12 with the 4
cross-origin ones all reaching the user in the notice (12/12 reach). Pre-registered prediction
"v3 ≤ v2-verified on attacks" holds on both frontier models (tie at 0%).

## 21 Oct 2026: why the gate trails provenance quarantine on poisoned LongMemEval

Frozen gate, Llama 3.1 8B: poisoned accuracy 45% (user-only 63%), adopts 36%. Each question has
3 poisoned rounds. Notices on adopted cases held 1 (21) or 2 (20) of the 3; with all 3 contested
the agent never adopted (0 of 7; flagged 7). 41 of 43 adoptions had a notice. So the cause is
partial contesting: the conflict check misses some planted rounds, which then reach Llama with
an inline label only. (An earlier draft sentence blaming "rounds that contradict nothing" was
wrong and has been replaced.)

## 21 Oct 2026: MemShield-Bench (external attacks, not written by us), gate model qwen3-4B

- 42 poisoned rewrites of a stored clean entry, arriving from another origin: 35/42 contested or
  rejected (33 rejected by the screen as instructions or preferences, 2 contested), 7 stored
  unverified with a label. v2-auto, v2-verified and v3 identical.
- Screening on the 179-entry test split, single entries from an untrusted origin: poisoned
  rejected 38/49 (backdoor triggers 13/23, all other types 25/26); **clean rejected 29/130 (22%)**:
  imperative best-practice advice ("Always use parameterized queries") reads as an instruction.
  A false-positive cost of rule (1) on knowledge-base content, to report.

## 21 Oct 2026: v3 on the exposed suites (designed after seeing these; not evidence per the pre-registration)

| Suite | allow-all | v2-verified | **v3** |
|---|---|---|---|
| qwen3-4B fooled / updates (reach) / recall | 38 / 95 / 98 | 9 / 76 (92) / 96 | **9 / 73 (92) / 96** |
| Llama 3.1 8B fooled / updates (reach) / recall | 42 / 91 / 94 | 25 / 72 (87) / 94 | **6 / 63 (88) / 94** |
| Enron replays fooled / real updates, qwen3 | | 24 / 77 | 24 / 77 |
| Enron replays fooled / real updates, Llama | | 18 / 77 | **3 / 77** |
| SMS / phishing relayed, Llama | | 25 / 30 | 25 / 30 (first-contact scams contradict nothing) |
| 80 background facts, qwen3: fooled / upd (reach) / recall (reach) | 28 / 85 / 90 | 12 / 70 (82) / 87 (88) | 12 / 68 (82) / 87 (88) |

Pre-registered large-store prediction (v3 recall reaching the user ≥ 88%) holds: 88%.

Automated adaptive attacks (qwen3-14B told how the gate works; 188 per model; final-adaptive):
fooled, qwen3 / Llama: allow-all 44 / 56, label-only 20 / 52, v2-auto 4 / 10, v2-verified 6 / 20;
v3 queued (v3-adaptive).

## 21 Oct 2026: deployment runs and v3 on LongMemEval

- **Mem0** (full benchmark through Mem0 2.2 with the gate in front, Kaggle): same verdict as the
  built-in store on 442 of 442 test scenarios, for qwen3-4B and Llama 3.1 8B alike (v3: qwen3
  9% fooled / 73% updates / 96% recall; Llama 6% / 63% / 94%).
- **Cost** (uncached, T4, qwen3-4B, 36-scenario subset): v3 adds 1.02 gate calls, ~241 tokens and
  0.55 s per memory write; v2-verified 1.15 calls, ~283 tokens, 1.39 s. The agent's own
  extraction and answer: 2.0 s per scenario.
- **LongMemEval, v3** (Llama): clean 62%, poisoned 45% (adopts 36%, flags 57%), evidence-untrusted
  14%: identical to v2-verified. Chat rounds hold several claims and skip pairwise verification
  in both versions, so this suite does not separate them (pre-registered evidence item 2 is
  uninformative).

## 22 Oct 2026: held-out models decide the final gate (v3)

Held-out agents, benchmark test split, fooled: Gemma 3 12B allow-all 51%, user-only 18%,
label-only 28%, v2-verified 7%, **v3 8%** (updates 58% answered / 75% reach, recall 82% = undefended);
Qwen3 14B 45 / 13 / 34 / 13 / **13%** (updates 70 / 87, recall 98%). Real data, Gemma: Enron
v2-verified 27% vs v3 16% (7/0, p = 0.016); SMS and phishing 36% for both. Qwen3 14B identical
on every suite. GPT-written families (54): Llama v2-verified 56% vs v3 11% (8/0, p = 0.008),
qwen3 28% vs 17%. Pre-registered rule applied: **v3 is the final gate** (17 paired wins, 1 loss).

Gate-aware attacks (20, written after the freeze), fooled with v3: qwen3 30% (no defence 80%),
Llama 55% (75%). By strategy, Llama: same-origin persistence 100%, pre-emption 80%, first contact
40%, reframed as an addition 0%. Persistence and pre-emption work by design of the rules (a
source may update itself; the first statement is the reference) and nothing is contested, so
the notice does not apply. Reported as an open limitation.

Haystack table now generated from the fixed run (baselines had been from before the background
fix). With the fix, v2-auto and v3 keep the same recall (87%); the earlier recall gain from
verification was mostly the bug.

## 22 Oct 2026: v3 on the automated adaptive attacks (last pre-registered held-out item)

188 attacks per model (qwen3-14B rewrites, told the gate's rules). Fooled, qwen3 / Llama:
allow-all 44 / 56, label-only 20 / 52, v2-auto 4 / 10, v2-verified 6 / 20, **v3 5 / 1**.
v3 vs v2-verified on Llama: 37 vs 1 discordant (p < 0.001); qwen3 2 vs 0. By strategy on Llama
(v3): addition 2%, same-source 0%, user-voice 0%. Held-out total: v3 56 paired wins, 2 losses.

## 22 Oct 2026: external datasets and a bigger gate model

- **Bigger gate model (negative):** Qwen3 14B as gate model for Llama 3.1 8B: fooled 21% vs 6%
  with Llama as its own gate model; it contests 38 planted claims vs 48 (uncontested 113 vs 104).
  For qwen3-4B unchanged (9% vs 9%). A larger model calls fewer contradictions.
- **MemoryAgentBench** (36 counterfactual edits): same-source corrections answered, qwen3 50%
  (no defence 56%), Llama 56% (36%); other-source updates reaching the user, qwen3 67%,
  Llama 89% (no defence 36%: Llama answers from world knowledge).
- **MemShield-Bench, Llama gate model**: 38/42 contradicting rewrites caught; screen rejects 19/49
  poisoned and 14/130 clean (qwen3 gate: 35/42, 38/49, 29/130).
- **Bug fixed** in scripts/paper_numbers.py: expected answers were looked up only in scenarios/ and
  scenarios-real/, so updates in the external, gate-aware and fresh sets that reached the user
  through a notice were scored as not reaching it. No other number changed.

## 22 Oct 2026: Memory-Rebirth revoked-policy situations (4 models)

27 situations (9 policies × same-source / user / other-source replacement). Current policy in
the answer, of 27, v3 / no defence / no outside memory: qwen3-4B 27/27/25, Llama 26/25/26,
Gemma 24/24/27, Qwen3 14B 22/25/26. The models choose the safe action without any memory, so
the set separates little. Of v3's 9 losses, 5 are the screen rejecting the stricter policy as
an "instruction" ("Customer PII must never leave the internal network") after the permissive
one was stored as a fact. Same cost as MemShield's clean rejections: rule 1 is for personal facts.
LongMemEval-qwen3 errored again (Kaggle served the old dataset version without run_config.json);
re-pushed.

## 24 Oct 2026: LongMemEval with qwen3-4B (UUA protocol)

Accuracy (planted answer adopted), allow-all / user-only / v3: clean 54/54/54; poisoned
2 (96) / 54 (8) / 25 (64); evidence untrusted 2 (96) / 11 (2) / 8 (74). The gate beats no
defence but not provenance quarantine, and on untrusted evidence it loses to it (8 vs 11),
unlike Llama (14 vs 11). 53 of 77 poisoned adoptions had no notice (no planted round judged to
contradict a stored one); in 59 of 77 qwen3 labelled the answer unverified yet gave it.
The conflict check does not carry over to whole chat rounds; the paper no longer implies a
LongMemEval benefit beyond "better than no defence".

MemForm: the Kaggle run hit the 12-hour limit and was cancelled before finishing.

## 28 Oct 2026: MemForm (provenance hidden), thymus as write-time defence

150 MCQ cases (30 per interface), qwen3-4B, each record its own unauthenticated origin.
ASR 63% -> 41% average; clean accuracy 100% -> 85% (41% of 1890 records rejected, 16%
quarantined: decision rules read as instructions). By interface (undefended -> gate):
Content P1 86 -> 0; Evidence P2 85 -> 77; Scope P3 69 -> 37; Selection P4 68 -> 57;
Path P5 6 -> 31 and clean accuracy 44% (worse than no defence: withholding breaks merging).
Stratification, not the average, is the honest result. keyword_filter and llm_judge baselines
re-queued (first attempt crashed on a shared output dir; 12-h run before that was cancelled
at Kaggle's limit during MemForm's own five defences).

## 29 Oct 2026: literature sweep (latest 2026 work), 11 papers added

Searched arXiv for post-cutoff work on memory poisoning, updates/conflicts, provenance, user
warnings, and Hindi/Hinglish scam data. Added and positioned: Supersede (2606.27472), TEPA
(2608.07429, = any-origin replacement, our attackable ablation), FEB-30 (2610.22209, scores the
store as our write-level results do), MemTxn (2607.27834), LatticeMind (2608.08236, contested
status at write time but resolved in-system), Memory Trust Gap (2609.01852, bigger models
over-trust stale memories), control-plane study (2606.15903), Eywa (2605.30771), MINJA
robustness study (2601.05504), sleeper poisoning (2605.15338), Inspect India Evals (2607.25375).
Softened the Hindi/Hinglish claim: scam *classification* data exists; no agent-memory or update
benchmark. None of the 11 proposes disclosure to the user or pairs real/fake updates, so the
contribution claims stand. Titles/authors pulled from arXiv abs pages; verify with the other 17
in docs/citations-to-verify.md.

## 29 Oct 2026: 120 blind held-out labels (author), grader agreement

Author labelled all 120 held-out replies blind (model/defence/verdict hidden; document form of
eval/label.html). Labels: 41 correct, 11 outdated, 13 unknown, 20 adopted, 1 caveated,
9 disclosed, 25 absent. Grader (hybrid, qwen3-4b): pass/fail 94%, exact 91%, keywords alone
89%. 7 pass/fail flips: 5 lenient (incl. 2 Hindi adopted->absent, library-due-date outdated->
correct x2), 2 harsh (flagged->adopted). Full output: eval/heldout_agreement.txt.
\heldoutSentence filled. The author's close-call notes are in the session transcript.
