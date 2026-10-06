# Disclose, Don't Decide: telling real updates from poisoned ones in AI assistant memory

**Safal Gupta**, VIT · one-page summary for a prospective faculty mentor · October 2026

## The problem

AI assistants now remember things across chats (ChatGPT, Claude, Gemini; libraries such as
Mem0). Anyone who can put text in front of the assistant (an email, a web page, an SMS, another
user of a shared assistant) can plant a false "memory" that the assistant later repeats as
fact. OWASP lists this as a top agentic-AI risk (ASI06, Memory & Context Poisoning).

The hard part: **real updates arrive through the same channels as attacks.** "Your parcel is
delayed" and "your parcel was cancelled, pay the fee here" are both emails that contradict a
stored fact. Defences that block untrusted content also block real updates.

**The gap.** Research on memory updates (LongMemEval, Supersede, MemConflict) assumes every
update is honest; research on memory poisoning (MemGauge, Utility Under Attack, MemPoison,
MemSecBench) assumes every update is an attack. We checked about 35 papers from 2024–2026:
none evaluates both on the same facts.

## The idea

A memory gate that, instead of only *storing or blocking*, can **disclose**: keep a contested
claim, never present it as fact, and tell the user who said it. Plus two rules: content from
tools can never speak for the user, and a fact can be replaced only by the user or by the
(authenticated) source that stated it. The gate's guarantees are checked mechanically on
thousands of random write sequences.

## Evidence so far (measured, October 2026)

- **Benchmark:** 491 matched scenarios: 90 everyday fact families, each with a real update
  and an attacker's look-alike twin, including 30 Indian families (UPI, KYC, electricity,
  FASTag…) in English, Hindi and Hinglish, and 16 attacks written against the gate itself.
- **Qwen3-4B, 442 held-out scenarios:** no defence 38% of attacks succeed; blocking all tool
  content 14% but only 30% of real updates survive; **our gate 8%, with 94% of real updates
  still reaching the user.**
- **Frontier models:** Claude Opus 5.5 states 58% of fake updates as fact with no defence,
  GPT-6-Astra 50%; with the gate, 0% on a 36-scenario subset (plus 16 adaptive attacks for
  GPT), with real updates kept.
- **Ablations:** removing disclosure more than doubles attack success; hiding contested
  claims instead of disclosing them loses a quarter of real updates.
- **Real data (running):** LongMemEval with the exact poisoning protocol of Utility Under
  Attack (arXiv 2608.21230), a real SMS phishing dataset, and a study of real assistants'
  memory on the author's own accounts with responsible disclosure.

## Plan and ask

Target: **USENIX Security 2027** (paper due 26 January 2027). Code and data are complete
enough to review now (private GitHub repository, shared on request).

I would be grateful for your guidance as a mentor or co-author: reviewing the threat model
and claims, advising on statistics and writing, and helping with an ethics review if we add a
small user study. About one hour every two weeks until submission.
