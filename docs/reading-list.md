# Reading list

## Read first (weeks 1–2)

1. **MINJA: Memory Injection Attacks on LLM Agents via Query-Only Interaction** (Dong et al., 2025)
   [arXiv:2503.03704](https://arxiv.org/abs/2503.03704)
   The attacker is just another user asking questions, yet 98.2% of malicious records get injected
   and 76.8% get acted on. Read for: the bridging-step trick. It is why the `minja-query`
   scenario beats the `user-only` gate.

2. **AgentPoison: Red-teaming LLM Agents via Poisoning Memory or Knowledge Bases** (Chen et al., NeurIPS 2024)
   [arXiv:2407.12784](https://arxiv.org/abs/2407.12784)
   Over 80% attack success with under 0.1% of memory poisoned. Read for: how retrieval itself is
   attacked with optimised trigger phrases. A write-gate does not cover this, so note the limits.

3. **Evaluating Memory in LLM Agents via Incremental Multi-Turn Interactions (MemoryAgentBench)** (Hu, Wang & McAuley, 2026)
   [arXiv:2507.05257](https://arxiv.org/abs/2507.05257)
   No memory system masters all four skills; selective forgetting is worst (at most 28% on
   multi-hop). Read for: the FactConsolidation task, a ready-made test of the "update" side.

4. **Reliable Post-Retrieval Assembly for Agent Memory: Separating Evidence Extraction from Policy Execution** (Reddy & Challaram, 2026; title corrected 12 Oct 2026)
   [arXiv:2606.01435](https://arxiv.org/abs/2606.01435)
   Version-aware, deterministic aggregation beats asking the model to resolve conflicts. Read for:
   the versioning part of the gate.

## Closest prior work: read before claiming anything is new

5. **Utility Under Attack: Agent Memory Poisoning and the Limits of Content Screening and Provenance Ranking** (Karunanidhi, Aug 2026)
   [arXiv:2608.21230](https://arxiv.org/abs/2608.21230)
   A four-stage content screen rejected 0 of 360 poisoned memories, and provenance weighting
   could not balance poisoning resistance against access to legitimate evidence. This is the
   closest paper to this project. Our difference: legitimate *updates* to existing facts, and
   quarantine and maturation rather than retrieval weighting.

6. **Understanding Stage-Wise Utility-Risk Trade-offs in LLM Agent Memory** (Zang et al., Aug 2026)
   [arXiv:2608.30177](https://arxiv.org/abs/2608.30177)
   Studies the utility-risk trade-off across the write, manage and retrieve stages on 11 models.
   Check how they measure utility, and whether conflicting updates are covered.

## Also useful

- **From Untrusted Input to Trusted Memory: A Systematic Study of Memory Poisoning Attacks in LLM Agents** (2026), [arXiv:2606.04329](https://arxiv.org/abs/2606.04329)
- **MemSentry: A Framework for Detecting Persistent Memory Poisoning in Agentic AI** (2026), [arXiv:2609.08747](https://arxiv.org/abs/2609.08747)
- **Continual Learning Bench** (Asawa et al., 2026), [arXiv:2606.05661](https://arxiv.org/abs/2606.05661): agents fail to reuse what they learn; naive in-context learning beats memory systems.
- **Mem0** ([GitHub](https://github.com/mem0ai/mem0)): the baseline to compare against in weeks 9–10.
- **OWASP Top 10 for Agentic Applications (2026)**, ASI06 Memory and Context Poisoning.
