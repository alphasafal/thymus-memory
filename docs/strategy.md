# Strategy: from project to top-venue paper with real impact

Written 5 October 2026. Revisit every two weeks.

## Honest odds

- **Best-paper awards** go to roughly 1–2% of *accepted* papers. Nobody can promise one.
  What we can control is building every part of the paper to the standard award winners share.
- **Acceptance at a top venue** is a realistic goal if the experiments below are completed.
- **Real-world impact** does not depend on awards. It comes from people using the benchmark
  and the gate. That part we can make very likely.

## What award-winning papers have, and how we match each

| Trait | Our plan |
|---|---|
| One crisp, surprising idea | "Disclose, don't decide": a third outcome beyond store/block moves the safety–usefulness trade-off |
| A problem people care about | Memory poisoning (OWASP ASI06) + India's ₹53,000-crore fraud problem + a legal hook (DPDP right to correction) |
| Rigorous evidence | 300+ matched scenarios, 6 defences, 5+ models from 4 families, ablations, confidence intervals and significance tests |
| Trustworthy measurement | Grader validated against three independent labellers: a human, Claude, GPT |
| Honesty about limits | Scenarios built to make our own gate fail (cross-origin updates, spoofed senders) and reported prominently |
| A reusable artifact | Open benchmark + leaderboard + an installable gate that drops into existing memory libraries |
| Excellent writing | Several review rounds: Claude reviewer, GPT reviewer, and ideally a faculty mentor |

## Target venue

**Primary: USENIX Security 2027, Cycle 2.** Registration 19 January 2027, paper 26 January 2027
(13 pages + mandatory Open Science appendix). Top-tier security venue that values real-world
impact and runs artifact evaluation (badges). It has historically given Distinguished Paper
awards and the Internet Defense Prize for practical security research.

**Alternatives** (never submit the same paper to two venues at once):
- ACL 2027 via ACL Rolling Review (January 2027), if the multilingual angle becomes the headline.
- NeurIPS 2027 Datasets & Benchmarks track (around May 2027), if the benchmark is the headline.
- If rejected: revise with reviewer feedback and resubmit (ACM CCS, IEEE S&P, or the above).

Check each call for papers for anonymity and preprint rules before posting anything publicly.

## Experiments still needed

1. **Main table:** 6 defences × all scenarios on `qwen3:4b-instruct` (local, overnight).
2. **Model breadth:** `qwen2.5:3b` and `qwen3:4b-instruct` (local); Claude Sonnet (Pro subscription,
   capped); GPT (ChatGPT Plus via the Codex CLI, if it works cleanly); 8–14B open models (Llama,
   Qwen, Gemma) on Kaggle's free GPUs.
3. **India extension:** 30 families × 3 languages (English, Hindi, Hinglish). Batch 1 has 12.
4. **Adaptive attacker:** attacks designed by someone who knows how the thymus gate works.
5. **Long memory:** 100 background memories per scenario, where bounded occupancy should matter.
6. **Ablations:** thymus without disclosure, without the same-origin rule, without the claim classifier.
7. **Grader validation:** 100 held-out replies labelled blind by you, a Claude helper and GPT;
   report agreement (Cohen's kappa) and grader accuracy.
8. **Statistics:** bootstrap confidence intervals; McNemar tests between defences.
9. **Practical demo:** the gate running inside an open-source memory library (Mem0).

## Who does what

| You | Claude (this project) |
|---|---|
| Create accounts: GitHub, Hugging Face, Kaggle (phone-verified), arXiv, ORCID; later OpenReview and the USENIX submission site | Code, experiments, analysis, figures, first drafts |
| Review Hindi/Hinglish wording (`docs/hindi-review.md`) | Write scenarios in all three languages |
| Label 100 replies blind (about 2 hours) | Run graders and agreement statistics |
| Run labelling and reviews in ChatGPT Plus (uploading files I prepare) | Prepare the files and prompts for ChatGPT |
| Find a faculty mentor or co-author (strongly recommended) | Prepare a one-page summary to send them |
| Keep the Mac plugged in for overnight runs | Schedule and monitor runs |

## Timeline to 26 January 2027

| Weeks | Dates | Goal |
|---|---|---|
| 1–2 | 6–19 Oct | Main local results; India batch 2; Hindi review; adaptive attack design |
| 3–4 | 20 Oct–2 Nov | Kaggle models; Claude and GPT subsets; human + model labels |
| 5–6 | 3–16 Nov | Ablations, long memory, Mem0 demo, statistics |
| 7–9 | 17 Nov–7 Dec | Full paper draft and figures; artifact packaging |
| 10–11 | 8–21 Dec | Review rounds (Claude, GPT, mentor) and revisions |
| 12–14 | 22 Dec–11 Jan | Polish; Open Science appendix; artifact checklist |
| 15 | by 19 Jan | Register the paper |
| 16 | by 26 Jan | Submit |

## Impact plan (independent of acceptance)

- Public GitHub repository (open licence) and an installable package.
- Hugging Face dataset + a leaderboard others can submit their defences to.
- A plain-language guide for Indian developers building assistants that read SMS, email or WhatsApp.
- A contribution to the OWASP Agentic Security guidance on memory poisoning (ASI06).
- Write-ups for developer communities and LinkedIn once the paper is public.
