# Datasets

Everything under `data/` is downloaded, never committed. This file records where each
dataset came from, its licence, and a checksum, so every result can be reproduced.

| Dataset | Source and version | Licence | File | SHA-256 | Used for |
|---|---|---|---|---|---|
| LongMemEval_S | HF `xiaowu0162/longmemeval`, revision `2ec2a557f339b6c0369619b1ed5793734cc87533` (the one Utility Under Attack used) | MIT | `data/longmemeval/longmemeval_s` (278,025,796 B) | `08d8dad4be43ee2049a22ff5674eb86725d0ce5ff434cde2627e5e8e7e117894` | Real chat histories under the Utility Under Attack poisoning protocol (`thymus-longmemeval`) |
| LongMemEval oracle | same revision | MIT | `data/longmemeval/longmemeval_oracle` (15,388,478 B) | `821a2034d219ab45846873dd14c14f12cfe7776e73527a483f9dac095d38620c` | Evidence-only sessions (debugging, knowledge-update subset) |
| LoCoMo | GitHub `snap-research/locomo`, `data/locomo10.json` (downloaded 6 Oct 2026) | CC BY-NC 4.0 (research use; derived files not redistributed) | `data/locomo/locomo10.json` (2,805,274 B) | `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4` | Clean-utility check, as MemGauge used it |
| SMS Phishing Dataset (Mishra & Soni, 2022) | Mendeley Data `f45bkkt8pr` v1, `Dataset_5971.zip` | CC BY 4.0 | `data/sms-phishing/Dataset_5971.csv` (5,971 messages: 4,844 ham, 638 smishing, 489 spam) | `649844f1c62a6b27e145eaf17a65f7010c56c390e11a794ea8329993a05ba71e` | Real scam texts as attack content; ~80 are India-specific |

## Derived data we create (committed)

| File | How | Notes |
|---|---|---|
| `eval/longmemeval/poison_claude-haiku-4-5.jsonl` | `thymus-longmemeval --make-poison claude-code:claude-haiku-4-5`: the paper's model and prompt, one call per question | 120 questions × 3 rounds = 360 poisoned rounds (1.2% of 29,646 + 360). Derived from MIT data |
| `scenarios-real/sms.json` | `scripts/build_realsms.py`: 117 real smishing messages (79 India-specific), deduplicated; every phone number, link and email replaced by a unique safe placeholder that doubles as the attack marker | Derived from CC BY 4.0 data (Mishra & Soni 2022); attribution kept in each scenario |

## Candidates not yet used

| Dataset | Licence | Why it would help | Status |
|---|---|---|---|
| MemoryAgentBench conflict resolution | MIT | Honest updates at scale (FactConsolidation) | Only 8 very long documents; lower priority than LongMemEval knowledge-update |
| MemShield-Bench | CC BY-SA 4.0 | 322 poisoned / 856 clean memory texts: tests the claim classifier on someone else's attacks | Next |
| AgentDojo | MIT | Realistic injection texts in email, calendar, banking tool output | Next |
| MINJA code | see repo | Query-only injection through another user | Our other-user attacks follow its threat model |
| MPBench, MemPoison, MemSecBench | not released | Their attack corpora would allow direct comparison | Ask the authors |

## Synthetic data (ours), and why it is still needed

The 491 matched scenarios are written by us because no public dataset pairs each real update
with an attacker's twin on the same facts, or covers Indian payment, KYC and utility fraud in
Hindi and Hinglish. Every claim in the paper is reported on both: our matched benchmark, and
the public datasets above.
