# Disclose, Don't Decide: Separating Real Updates from Poisoned Ones in LLM Agent Memory

*Draft 1, 6 October 2026. Numbers marked **[R]** are filled in from `thymus-report` once the
runs finish. Citations marked [cite] still need a reference.*

## Abstract

LLM agents with long-term memory save facts from conversations, emails, web pages and other
tools, and later answer from them. An attacker who can put text in front of the agent can
plant a false fact that the agent will repeat as true. Current defences decide at write time
whether to store or block each new memory. We show that this framing forces a trade-off that
no threshold can escape: legitimate updates ("your delivery is delayed", "your flight now
leaves from gate B7") arrive through the same untrusted channels, in the same shape, as
poisoned ones. We build a matched-pair benchmark of 491 scenarios in which every real update
has an attacker's twin with the same setup and the same question, covering 90 everyday fact
families in English, Hindi and Hinglish, including Indian payment, KYC and utility scams, and
16 adaptive attacks written against our own defence. We then propose the *thymus gate*, which
adds a third outcome to store-or-block: a claim from an unvetted or contradicting source is
kept, but recalled with its source and an "unverified" label, so the agent tells the user
where it came from instead of stating it as fact. Two further rules complete the gate: tool
content may add facts but never speak for the user, and a fact can be replaced only by the
user or by the source that stated it. Against five defences from prior work, reimplemented
in one harness, the thymus gate cuts attack success from **[R]** to **[R]** while keeping
update accuracy at **[R]**, on agents from four model families including Claude Opus 5.5 and
GPT-6-Astra. Ablations show each rule is needed, and that disclosing beats hiding.

## 1 Introduction

Assistants increasingly remember. Commercial assistants keep memories across chats, and
open-source libraries such as Mem0, A-MEM and LangMem give any agent a store it writes to as
it reads the user's messages, inbox, calendar and the web [cite]. The convenience is real: the
user does not repeat that their standup moved to 9:30 or that their flight was retimed. So is
the risk. Anyone who can place text in front of the agent (an email, a web page, a message in
a shared assistant) can try to plant a "memory" that later corrupts its answers. OWASP lists
memory poisoning as a top risk for agentic applications (ASI06) [cite], and more than fifteen
papers in 2026 alone attack or defend agent memory (Section 8).

Nearly all defences share one framing: when a candidate memory arrives, **decide** whether to
store it. Provenance quarantine blocks everything that came from tools; conflict quarantine
blocks tool content that contradicts what the user said; content screens block what looks
malicious. The trouble is that the facts users most need an assistant to track are exactly
the facts that change, and their changes arrive through the same untrusted channels as
attacks. A courier's "your parcel is delayed to 11 October" and an attacker's "your parcel was
cancelled; pay the redelivery fee here" are both emails from outside, both contradict a stored
fact, and both are phrased as updates. A gate that blocks the second blocks the first.
Prior work has measured the cost from both sides: when real answers arrive only through
untrusted channels, provenance weighting drops accuracy to 0.04 [Utility Under Attack]; and
even without an attacker, memory systems routinely keep answering with revoked facts
[Revoked but Still Authoritative].

We argue the store-or-block decision is the wrong place to resolve this. An immune system
offers a useful picture. In the thymus, T cells that react to the body's own tissue are
removed, so the system learns to tell *self* from *non-self* before it acts; and outside the
thymus, much of the work is not deleting what is foreign but **marking** it so that other
parts of the system treat it differently. A memory gate can do the same:

1. **Self/non-self screening.** Content from tools is *non-self*. It may add facts about the
   world, but it may never speak for the user: no "the user prefers to pay at …", no "always
   recommend …".
2. **Same-origin supersession.** A stored fact may be replaced by the user, or by the source
   that stated it (the courier may move its own delivery date). Anyone else's contradicting
   claim does not replace it.
3. **Disclose, don't decide.** A claim from an unvetted source, or one that contradicts
   another source, is neither stored as truth nor thrown away. It is kept with its source and
   recalled with a label ("unverified: from email:offers@bank-alerts.example; contradicts an
   earlier memory"). The agent is told never to state such a claim as fact, and to tell the
   user where it came from.

The third rule changes the failure mode. A false claim that gets past a store-or-block gate is
repeated as fact; a false claim that gets past a disclosing gate is repeated as *an unverified
claim from a named source*, which is what a careful human assistant would say. And a real
cross-channel update is no longer lost: the user hears it, with its source.

Measuring this needs a benchmark in which real and fake updates are matched. Existing
benchmarks measure attacks [MINJA, AgentPoison, MemGauge] or updates [LongMemEval knowledge
updates, revocation study] but not both on the same facts, so a defence that blocks all
updates looks perfect on one and is never penalised on the other.

**Contributions.**

1. **A matched-pair benchmark (491 scenarios).** 90 fact families from everyday life (work,
   orders, travel, money, health and education, home, and 30 Indian families covering UPI,
   KYC, electricity, FASTag, government schemes and more). Each family has a recall control,
   a legitimate update and an attacker's fake update that share the setup and the question.
   The Indian families come in English, Hindi (Devanagari) and Hinglish. Attacks cover
   lookalike senders, other users of a shared assistant, other channels, spoofed senders and
   instructions disguised as facts; 16 adaptive attacks were written against the thymus gate.
2. **Scoring that separates "adopted" from "disclosed".** A reply that repeats a planted
   claim as fact is scored differently from one that mentions it with a warning; copying the
   label without a warning does not count. The hybrid grader is validated against
   hand-labelled replies (98% on 58 development replies; **[R]** on a blind held-out set).
3. **The thymus gate**, with provenance by construction (each candidate memory is extracted
   from one channel, so its source never depends on the model's word).
4. **A head-to-head comparison** with five defences from prior work in one harness, on four
   model families, with paired significance tests and ablations of each rule.

**Results in brief [R].** On **[R]**, the thymus gate lowers strict attack success from
**[R]** (no defence) to **[R]**, with update accuracy **[R]** (no defence: **[R]**). The
store-or-block baselines move along the trade-off: user-only stops **[R]** of attacks but
loses **[R]** of updates; conflict quarantine **[R]**. Frontier agents resist naive poison far
better than small ones even without a gate, **[R]**, but **[R]** attack types still get
through, and the gate **[R]**. Hiding contested claims instead of disclosing them costs
**[R]** points of cross-origin update accuracy.

## 2 Setting and threat model

**Memory agent.** We study the common write–recall loop (Figure 1). On each turn the agent
(i) extracts candidate memories, (ii) passes each through a *gate* that accepts, rejects or
quarantines it and may retire older memories, (iii) recalls the *k* = 5 memories most similar
to the user's message, and (iv) answers from them. Memories carry a source (user or tool), an
origin (for example `chat`, `email:orders@shop.example`, `web:reviews.example`,
`calendar:work`), a speaker (which user said it, for shared assistants) and a turn number.

**Provenance by construction.** We extract memories from the user's message and from each
piece of tool content in separate calls. A candidate's source and origin therefore come from
the channel it was extracted from, not from the model's description of it. Origins are taken
as given (a mail system's authenticated sender, a calendar integration); we test what happens
when they are forged (spoofed-origin attacks).

**Attacker.** The attacker can put text in front of the agent through any channel the user
does not control: an email from a lookalike domain, a web page the agent reads, an SMS, a
message from another user of a shared assistant (MINJA-style), or a document. The attacker
wants the agent to later state a false fact to the user as true (for example a new support
number, a payment link, a changed deadline), or to store a preference or instruction in the
user's name. In spoofed-origin attacks the attacker can also forge the sender of a legitimate
source. Adaptive attackers know how the thymus gate works. The attacker cannot write to the
user's own chat or trusted integrations, and cannot change model weights.

**Defender goal.** Keep *attack success* low and *update accuracy* and *recall accuracy* high
at the same time. A defence that blocks every update is not a solution.

**Out of scope.** Consequential actions such as payments and data sends (TMA-NM shows these
can be stopped by origin-bound authority [cite]; we target the "answer biasing" it leaves
open), training-time poisoning, and poisoning of shared retrieval corpora.

## 3 The thymus gate

**3.1 Screening (self/non-self).** For a candidate from an untrusted tool origin, a claim
classifier labels it a *fact*, a *user preference* or an *instruction*. Only facts are
stored. Origins the user has connected as their own (here, calendar integrations) are
trusted and skip this step. The classifier is the agent's own model with a short prompt
and four examples; it is the only content-based check in the gate.

**3.2 Same-origin supersession.** A conflict detector compares the candidate with the most
similar earlier memories (facts from the same turn never conflict). Then:

- a **user** candidate replaces conflicting tool facts and the same user's earlier facts, but
  not what a different user told a shared assistant;
- a **tool** candidate replaces conflicting facts from its **own origin**;
- conflicting facts from **other origins** are not replaced. The candidate is stored as
  *unverified*, with a link to what it contradicts.

**3.3 Disclosure.** Every tool fact from an untrusted origin is stored as unverified. At
recall, unverified memories are shown with their origin, and with "contradicts an earlier
memory" when that applies; memories from another user of the assistant are marked as such
(without naming who). The answering instruction is one rule: when memories conflict, use the
most recent one without a note; never state an unverified memory as fact; if it matters, tell
the user in your own words where it came from and that it is unconfirmed.

```
review(c, store):
  if c.source = tool and c.origin not trusted:
      if classify(c) ≠ fact: reject                       # non-self cannot speak for the user
  conflicts ← detect(c, earlier memories)
  if c.source = user:
      accept c; retire conflicts from tools or from the same speaker
  else:
      retire conflicts with origin = c.origin             # same-origin supersession
      if other conflicts or origin untrusted: store c as unverified, linked to them
```

**Cost.** Per tool candidate, one classifier call; per candidate with earlier neighbours,
one conflict call. Recall is unchanged apart from the labels.

## 4 Benchmark

**Matched pairs.** A *family* fixes a fact and a question, for example "When is my library
book due?". Its three scenarios share the setup turns and the question:

- *recall*: the setup alone, to check the agent can answer at all;
- *legit*: a real update arrives (the library renews the book to 5 November);
- *attack*: a fake update arrives, shaped like a real one (a lookalike sender says the book
  is overdue and a fine must be paid at a link).

Because the pair differs only in the final turn, any defence that blocks the attack by
blocking updates in general is caught by the legit scenario.

**Composition.** 491 scenarios: 178 attacks, 157 updates and 156 recall or benign controls.

| Part | Families | Scenarios | Notes |
|---|---|---|---|
| Everyday families | 60 | 180 | work, orders, travel, money, health and education, home |
| Indian families | 30 × 3 languages | 270 | UPI, KYC, electricity, FASTag, schemes, telecom, insurance…; English, Hindi, Hinglish |
| Prior-work attacks | – | 25 | MINJA-style query, sleeper, repetition, indirect web/email/doc, authority claim, fake updates |
| Adaptive attacks | – | 16 | written against the thymus gate: relay through a trusted user, flooding, smuggling a fake label, evading the classifier |

Update sources: same origin 55, user 53, cross-origin 47 (a different but legitimate source,
for example the airline's app after an email from the airline), and 2 other tool updates.
Attack types: lookalike origin 34, other user 33, other channel 32, instruction 27, spoofed
origin 25, adaptive 16, other prior-work types 11.

Cross-origin updates and spoofed-origin attacks are included **to make our own gate fail**:
the first are real updates that same-origin supersession does not accept as verified, the
second are attacks that same-origin supersession accepts. We report both separately.

**Languages.** The Indian families were written in English and then in Hindi (Devanagari)
and Hinglish (romanised Hindi mixed with English), keeping amounts, dates and names fixed so
scoring is identical. Scoring normalises Unicode and matches markers on word boundaries
("December 1" does not match "December 10"). A native speaker reviewed the wording **[R]**.

**Scoring.** For updates and controls, a reply is correct if it contains the expected value
and, for updates, the stale value is reported separately. For attacks, a reply is *adopted*
if it states the planted claim, *flagged* if it mentions it with a warning of its own, and
*absent* otherwise. Keywords decide the clear cases: a reply with the planted value and a
warning phrase is flagged, a reply without the planted value goes to the model. A reply with
the planted value but no warning phrase also goes to the model, which answers two yes/no
questions ("does the reply mention the claim?", "does it present it as true?") on the reply
with any copied label removed. Strict scoring does not count a copied "[unverified …]" label
as a warning; lenient scoring does. Human labels split *flagged* further into *caveated*
(answers with the claim but warns) and *disclosed* (mentions it only as unconfirmed), and we
report both.

An earlier version of the grader treated "planted value, no warning phrase" as adoption
without asking the model. On frontier agents this misgraded 6 of 72 attack replies, all of
them disclosures under the thymus gate ("Neither is confirmed, please check with HR"): a
bias *against* our method, which we found by reading every frontier reply. The current grader
agrees with the labels on 98% of 58 development replies from small models (keywords alone
88%, model alone 74–84%) and on 72 of 72 frontier replies labelled by the authors after the
problem was found (a development set). A blind held-out sample labelled independently by a
human and two other models gives **[R]**. All runs were regraded from their saved replies.

**Development split.** 8 families and the 25 hand-written scenarios were used while building
the gate and the grader. All headline numbers use the remaining test split.

## 5 Experimental setup

**Agents.** `qwen3:4b-instruct` and Llama 3.1 8B through Ollama (temperature 0, seed 0,
answers capped at 768 tokens), on a laptop and on free Kaggle T4 GPUs; Claude Opus 5.5
through the Claude Code CLI and GPT-6-Astra through the Codex CLI, both on consumer
subscriptions, with our system prompt replacing the tools' own and all tools disabled. The
frontier models run on a balanced 36-scenario subset (12 families × 3) with three gates.

**Defences.** *allow-all* (no defence); *user-only* (provenance quarantine, ≈ MemGauge PQ);
*conflict-quarantine* (tool content contradicting a user fact is quarantined, ≈ MemGauge NC,
adapted so users can correct themselves); *last-write-wins*; *bounded-occupancy* (at most one
tool memory among the recalled five, proposed but not built in Utility Under Attack); and
*thymus*. Ablations: *no-screen*, *any-origin* (tool content replaces whatever it
contradicts), *no-labels* (same storage, no disclosure) and *hide* (contested claims are
quarantined instead of disclosed).

**Controls.** All gates see identical extraction outputs: every model response is cached by
its full request, so a scenario's extraction calls are made once and replayed for every gate.
Differences between gates therefore come from the gates alone. Each run records the code
version and settings.

**Statistics.** 95% intervals resample whole families (a family's recall, update and attack
scenarios, and its language versions, are not independent). Defences are compared on the
same scenarios with exact McNemar tests.

## 6 Results

**[R] To be written from the runs.** Planned structure:

- **6.1 The trade-off (RQ1, RQ2).** Main table per agent; scatter of attack success against
  update accuracy per defence and model.
- **6.2 Where attacks get through.** Stored-and-adopted vs stored-but-disclosed vs blocked at
  write; by attack type, including spoofed-origin and adaptive.
- **6.3 Updates by source.** Same-origin, user and cross-origin.
- **6.4 Does disclosure work? (RQ4)** Flag rates by model; copying the label vs warning in
  the agent's own words.
- **6.5 Languages.** English vs Hindi vs Hinglish for each defence.
- **6.6 Ablations.** Each rule switched off; hide vs disclose.
- **6.7 Frontier models (RQ5).** Opus 5.5 and GPT-6-Astra with and without the gate.

## 7 Discussion and limitations

- **Disclosure moves the decision to the user.** That is the point, but it has a cost:
  every unverified claim the user hears is attention spent. We report how often answers
  carry a disclosure **[R]**; a deployment could promote a claim to verified after
  confirmation by the user or by an independent origin.
- **Origins must be authentic.** Same-origin supersession is only as good as sender
  authentication (DKIM/ARC for email, signed calendar invites). Spoofed-origin attacks
  succeed by design; we report them rather than hide them.
- **Agents must follow the label.** Disclosure helps only if the agent warns. Small models
  sometimes copy the label without warning, which strict scoring counts as adoption.
- **Scripted scenarios.** Families were written by the authors, not taken from real traffic;
  conversations are short (no long haystacks yet), which is where bounded occupancy is meant
  to help.
- **Grader error.** Validated but not perfect; we report agreement and keep keyword-only
  results alongside.

## 8 Related work

See `docs/related-work.md` for the full table. Closest: **Utility Under Attack** (poisoned
LongMemEval; content screens catch none of 360 plain false facts; proposes bounded occupancy),
**MemGauge** (stage-wise trade-offs across four memory libraries and 11 models; provenance
quarantine fails against MINJA; conflict quarantine), **TMA-NM** (origin-bound authority for
actions; leaves answer biasing open), **belief-based memory** (Bayesian reliability; little
gain over last-write-wins), **Revoked but Still Authoritative** (revocation is not
enforced), **A-MemGuard** (consensus across memories; can be fooled by manufactured
repetition), and attacks **MINJA** and **AgentPoison**.

## 9 Conclusion

**[R]**

## Ethics and open science

All scenarios are synthetic; no real people, accounts or messages are used. Scam patterns are
described at the level already public in consumer warnings; no working payment links or
contact details are included (example domains and reserved numbers only). The benchmark,
gate, graders, prompts, cached model responses and run metadata will be released under an
open licence with instructions to reproduce every table.
