# Literature map: agent memory, updates and poisoning

Compiled 6 October 2026 from arXiv, ACL Anthology, OpenReview, Hugging Face and GitHub.
Every entry was opened and checked; claims about each paper are in its row. Detailed
quotes for the closest papers are in `docs/related-work.md`.

## The finding that frames the paper

Two research communities study the same moment, a stored fact meeting a newer claim, and
never meet:

- **Memory-update research assumes every update is honest.** Supersede, MemConflict, The
  Memory Trust Gap, MemoryAgentBench (conflict resolution), LongMemEval (knowledge update),
  Revoked but Still Authoritative: the question is whether the agent *adopts* the change.
- **Memory-poisoning research assumes every update is an attack.** MemGauge, Utility Under
  Attack, MPBench, MemPoison, MemSecBench, GhostWriter, PipePoison, TMA-NM, SMSR: the
  question is whether the agent *resists* it.

A deployed assistant faces both through the same channels. No paper we found evaluates
them together on the same facts.

## 1. Memory updates and conflicts (honest updates only)

| Paper | Venue / date | What it shows | Data |
|---|---|---|---|
| LongMemEval (Wu et al.) | ICLR 2025 | 500 questions over long chat histories; a *knowledge-update* type (78) where a fact changes | HF `xiaowu0162/longmemeval`, MIT |
| MemoryAgentBench (Hu et al.) | ICLR 2026 (arXiv 2507.05257) | Conflict resolution: single-hop GPT-4o agents ~60%, multi-hop ≤7% | HF `ai-hyz/MemoryAgentBench`, MIT |
| MemBench | ACL Findings 2025 (2506.21605) | Factual and reflective memory, participation vs observation | — |
| Supersede (Patel) | arXiv 2606.27472, Jun 2026 | "Memory-update gap": gpt-5.4 92% → 77% with bounded memory; trainable with RL | GitHub `Vrin-cloud/supersede` (built on LongMemEval KU) |
| MemConflict (Tao et al.) | arXiv 2605.20926, May 2026 | Dynamic, static and conditional conflicts across 6 memory systems | not stated |
| The Memory Trust Gap (Hu, Ramachandran) | arXiv 2609.01852, Sep 2026 | Models pick stale memory over authoritative current values 0.92–1.00 of the time; larger models are fooled *more* by newer-looking dates | RGB, MisBench |
| Revoked but Still Authoritative (Shen et al.) | arXiv 2609.08258, Sep 2026 | 5 memory systems, 9 models: no system enforces revocation by default | — |
| GroupMemBench | Microsoft Research 2026 | Multi-party conversations; knowledge update 27.1% | — |
| LoCoMo (Maharana et al.) | ACL 2024 | Very long two-person conversations with QA | GitHub `snap-research/locomo`, CC BY-NC 4.0 |

## 2. Memory poisoning: attacks and benchmarks

| Paper | Date | Key result | Data released? |
|---|---|---|---|
| MINJA (Dong et al.) | NeurIPS 2025 (2503.03704) | Query-only injection: 98.2% injection, 76.8% attack success | Code: GitHub `dsh3n77/MINJA` |
| AgentPoison | NeurIPS 2024 | Trigger-optimised RAG/memory backdoors | Yes |
| MPBench (Dash et al.) | 2606.04329, Jun 2026 | 3,240 attack cases, 6 classes, plus 2,997 benign; existing prompt-injection defences do not cover memory poisoning | Not found |
| GhostWriter / AM-Sentry (Torres et al.) | 2607.06595, Jul 2026 | ~98% injection, ~60% activation; save policy + retrieval screen | Not found |
| MemPoison (Gao et al.) | 2607.14651, Jul 2026 | 1,227 hand-validated cases, 10 model families | Not found |
| Bad Memory (Gadgil et al.) | 2607.14611, Jul 2026 | Claude Code and Codex memory files: planted payloads attack later sessions | — |
| MemSecBench (Chen et al.) | 2607.27080, Jul 2026 | 310 cases; malicious memory persists in 84.2%; repair varies by 41.3 pts across backends | Not found |
| PipePoison (Zang et al.) | 2609.00523, Sep 2026 | End-to-end optimised poisoning beats 8 defences | — |
| MemShield-Bench | HF `npow/memshield-bench`, CC BY-SA 4.0 | 1,178 entries (856 clean, 322 poisoned), 10 attack types | Yes |
| Benign Alone, Harmful Together | 2608.01759, Aug 2026 | Composition of individually benign experiences | — |

## 3. Defences

| Paper | Mechanism | Updates? |
|---|---|---|
| Utility Under Attack (2608.21230) | Write-time screen (0/360 caught), provenance ranking; proposes bounded occupancy | Shows the cost (0.0417) when real answers arrive untrusted |
| MemGauge (2608.30177) | Stage-wise policies across Mem0, A-MEM, LangMem, Hindsight | NC policy would block numeric updates |
| TMA-NM (2606.24322) | Origin-bound, label-propagating authority for actions | Answers "mitigated, not eliminated" |
| PPMF (2607.29167) | Provenance-preserving firewall for tool calls | Actions only |
| SMSR (2606.12703) | HMAC provenance + certified ablation | No |
| A-MemGuard (2510.02373) | Consensus across memories + lessons memory | No |
| Belief-based memory (2606.22030) | Bayesian reliability, provenance caps | Partly (sources of different trust) |
| MemAudit (2605.23723), MEMSAD (2605.03482), forensic signatures (2606.30566) | Detection and auditing after the fact | No |
| SuperLocalMemory (2603.02240) | Bayesian trust in multi-agent memory | No |

## 4. Prompt-injection benchmarks with realistic tool content

AgentDojo (NeurIPS 2024, MIT): 97 user tasks, 629 security cases in workspace (email,
calendar, drive), Slack, banking and travel. AutoDojo (2606.15057), AgentDyn (2602.03117).
Their injection texts are realistic tool content; memory turns a one-time injection into a
persistent one.

## 5. Real incidents and standards

- OWASP Top 10 for Agentic Applications (Dec 2025): **ASI06 Memory & Context Poisoning**,
  with the Gemini memory attack as its example; also ASI09 Human-Agent Trust Exploitation.
- OWASP GenAI Security Project: 2026 Top 10 for LLM Applications and an Agent Control
  Standard (Sep 2026).
- Google, Gemini 4 Argon (30 Sep 2026): "most resilient model yet against indirect prompt
  injections"; the announcement does not mention memory.

## 6. India: fraud and law (to cite from primary sources)

- Cyber-fraud scale: MHA answers in Parliament and NCRP/I4C figures (≈₹22,000 crore reported
  losses in 2024–25 per secondary reports of NCRP data); RBI Annual Report 2024–25 (bank
  fraud ₹36,014 crore in FY25 per secondary reports). **Both must be quoted from the official
  PDFs before use**; the government sites block automated fetching, so open them by hand.
- DPDP Act 2023: s. 8(3) duty to ensure "completeness, accuracy and consistency" of personal
  data used for decisions; s. 12 right to correction and updating.
- Common scam patterns (KYC expiry, electricity disconnection, parcel/customs, fake helpline,
  prize/lottery, loan recovery) appear in the real SMS dataset and in our India families.
