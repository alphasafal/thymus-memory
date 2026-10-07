# Disclose, Don't Decide: Separating Real Updates from Poisoned Ones in LLM Agent Memory

*Draft 2, 7 October 2026. Numbers marked **[R]** are filled in from `thymus-report` once the
runs finish. Citations marked [cite] still need a reference.*

## Abstract

LLM agents with long-term memory save facts from conversations, emails, web pages and other
tools, and later answer from them. An attacker who can put text in front of the agent can
plant a false fact that the agent will repeat as true. Most defences decide at write time
whether to store or block each new memory; the few that keep untrusted content with a label
use it to gate consequential actions, and leave the agent's answers open. We show that
store-or-block forces a trade-off that no threshold can escape: legitimate updates ("your delivery is delayed", "your flight now
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
in one harness, the thymus gate has the lowest attack success on every agent we test
(qwen3-4B 38% → 8%, Llama 3.1 8B 42% → 20%, Claude Opus 5.5 58% → 0%, GPT-6-Astra 50% → 0%)
while keeping plain recall, where provenance quarantine keeps only a quarter of it. On real
Enron update emails replayed from forged or lookalike senders, it is fooled 3% of the time
(no defence: 84%) while keeping 87% of the real updates (provenance quarantine: 0%). It cuts
real smishing relayed as genuine from 70% to 25% (Llama) and 19% to 10% (Opus,
Indian SMS). On LongMemEval under the Utility Under Attack protocol, keeping replaced
memories as labelled older versions doubles accuracy under poisoning (24% → 47%) at no
clean cost. A study of two production assistants finds the failure in the wild: ChatGPT
repeated 3 of 6 fake updates from memory in a new chat, once as something the user had said.

## 1 Introduction

Assistants increasingly remember. Commercial assistants keep memories across chats, and
open-source libraries such as Mem0, A-MEM and LangMem give any agent a store it writes to as
it reads the user's messages, inbox, calendar and the web [cite]. The convenience is real: the
user does not repeat that their standup moved to 9:30 or that their flight was retimed. So is
the risk. Anyone who can place text in front of the agent (an email, a web page, a message in
a shared assistant) can try to plant a "memory" that later corrupts its answers. OWASP lists
memory poisoning as a top risk for agentic applications (ASI06) [cite], and more than fifteen
papers in 2026 alone attack or defend agent memory (Section 8).

Most defences share one framing: when a candidate memory arrives, **decide** whether to
store it. Provenance quarantine blocks everything that came from tools; conflict quarantine
blocks tool content that contradicts what the user said; content screens block what looks
malicious. A second line of work keeps untrusted content but labels it, and uses the label to
stop that content from driving consequential actions such as payments [TMA-NM, PPMF]; its
authors note that false facts in the agent's *answers* are "mitigated, not eliminated".
Neither line asks what should happen when a fact legitimately changes. The trouble is that the facts users most need an assistant to track are exactly
the facts that change, and their changes arrive through the same untrusted channels as
attacks. A courier's "your parcel is delayed to 11 October" and an attacker's "your parcel was
cancelled; pay the redelivery fee here" are both emails from outside, both contradict a stored
fact, and both are phrased as updates. A gate that blocks the second blocks the first.
Prior work has measured the cost from both sides: when real answers arrive only through
untrusted channels, provenance weighting drops accuracy to 0.04 [Utility Under Attack]; and
even without an attacker, memory systems routinely keep answering with revoked facts
[Revoked but Still Authoritative].

We argue the store-or-block decision is the wrong place to resolve this. The immune system
offers a useful picture. In the thymus, developing T cells that react strongly to the body's
own proteins are eliminated, so the system learns to tell *self* from *non-self* before it
acts. And much of the response to foreign material works by **marking** it: antibodies tag a
pathogen so that other cells recognise and handle it. A memory gate can do the same:

1. **Self/non-self screening.** Content from tools is *non-self*. It may add facts about the
   world, but it may never speak for the user: no "the user prefers to pay at …", no "always
   recommend …".
2. **Authenticated same-origin supersession.** A stored fact may be replaced by the user, or
   by the source that stated it (the courier may move its own delivery date), and only when
   the channel authenticates that source. Anyone else's contradicting claim, and a forged
   sender, does not replace it. A replaced fact is retired; a replaced memory that also holds
   other facts is kept and marked as an older version.
3. **Disclose, don't decide.** A claim from an unvetted source, or one that contradicts
   another source, is neither stored as truth nor thrown away. It is kept with its source.
   Untrusted facts are recalled with their origin; *contested* claims are withheld from the
   answering model and disclosed by the system in a notice ("I also have unconfirmed
   information that contradicts this: a message from ⟨origin⟩ said ⟨claim⟩").

The third rule changes the failure mode. A false claim that gets past a store-or-block gate is
repeated as fact; a false claim that gets past a disclosing gate reaches the user as *an
unverified claim from a named source*, which is what a careful human assistant would say. And
a real cross-channel update is no longer lost: the user hears it, with its source. Because
the system, not the model, writes the notice, this works even for models that ignore labels.

Measuring this needs a benchmark in which real and fake updates are matched. Existing
benchmarks measure attacks [MINJA, AgentPoison, MemGauge] or updates [LongMemEval knowledge
updates, revocation study] but not both on the same facts, so a defence that blocks all
updates looks perfect on one and is never penalised on the other.

**Contributions.**

1. **A matched-pair benchmark (491 scenarios)**: 90 everyday fact families, 30 of them Indian
   (UPI, KYC, electricity, FASTag, government schemes) in English, Hindi and Hinglish. Each
   family has a recall control, a legitimate update and an attacker's twin sharing the setup
   and the question; 16 adaptive attacks target our own gate.
2. **Real-data evaluation on four public corpora**: 117 real smishing SMS (79 Indian), 112
   real phishing emails, 31 real Enron update emails each replayed from lookalike and forged
   senders (only provenance differs), and an exact reproduction of Utility Under Attack's
   LongMemEval protocol.
3. **The thymus gate**, whose rules are fixed and whose models only answer "is this a fact?"
   and "does this contradict that?", giving guarantees that hold whatever those models output
   (Section 3.4).
4. **A head-to-head comparison** with five defences from prior work in one harness, on four
   model families including Claude Opus 5.5 and GPT-6-Astra, with ablations, family-level
   bootstrap intervals and paired tests, and a grader validated against human labels.
5. **Evidence from production assistants**: in our own accounts, ChatGPT repeated 3 of 6
   fake updates from memory in a new chat, once as something the user had said.

**Results in brief.** Every store-or-block defence trades one failure for the other.
Provenance quarantine keeps a quarter of plain recall on the benchmark and *none* of the real
Enron updates; with no defence, a replayed Enron update fools Llama 3.1 8B 84% of the time.
The thymus gate has the lowest attack success on every agent (qwen3-4B 38% → 8%, Llama 42% →
20%, Opus 5.5 58% → 0%, GPT-6-Astra 50% → 0%) while keeping recall; on the Enron replays it is
fooled 3% of the time and keeps 87% of real updates. Disclosure is the active ingredient:
removing the labels returns attack success to the undefended level, and for a model that
ignores labels only the system notice works. On LongMemEval it doubles accuracy under
poisoning (24% → 47%) at no clean cost, once replacement respects memory granularity. Two
limits remain: when the real answer itself arrives untrusted, no provenance rule recovers it
(UUA's finding, which we reproduce), and the gate is only as good as the model making its
judgments, which costs most in Hindi and Hinglish (Section 6.6).

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
- a **tool** candidate replaces conflicting facts from its **own origin**, but only when the
  channel authenticates that origin (DKIM for email, a registered SMS sender ID, a signed
  calendar invite); a forged sender has the right origin and fails authentication;
- a replaced memory that is a single claim is retired; one that holds several facts (a
  whole chat round, a document) is kept and recalled as "older version: later updated", so
  replacing one fact never deletes the others;
- conflicting facts from **other origins**, and anything from a forged sender, are not
  replaced. The candidate is stored as *unverified*, with a link to what it contradicts. A
  user's statement that contradicts what a *different* user said is linked the same way.

**3.3 Disclosure.** Every tool fact from an untrusted origin is stored as unverified, and
recalled with its origin; memories from another user of the assistant are marked as such
(without naming who). *Contested* claims, those linked to something they contradict, are
not given to the answering model at all. The system appends a notice to the reply instead:
"I also have unconfirmed information that contradicts this: a message from ⟨origin⟩ said
⟨claim⟩. I have not used it in my answer; please check with the source." The model cannot
adopt what it never sees, and the user still learns of the claim and its source.

An earlier version (v1) passed contested claims to the model with an inline label and an
instruction to disclose them, and let any same-origin message replace a fact. Frontier
models and a 4B model followed the labels; Llama 3.1 8B did not (Section 6), and forged
senders exploited unauthenticated replacement. We report v1 alongside the final gate, and a
variant (v2-inline) that keeps v2's rules but discloses inline, to show how much disclosure
depends on the model when it is left to the model.

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

**3.4 Guarantees.** The models inside the gate decide *which* rule applies (is this a fact?
does it conflict?), never *what* a rule allows. So, with authentic origins and whatever the
detector and classifier output:

- **G1 (no cross-source overwrite).** Tool content from origin *o* only ever retires
  memories from origin *o*; it never retires a user's statement or another source's fact.
- **G2 (no cross-user overwrite).** A user only retires tool facts and their own statements,
  never what another user told a shared assistant.
- **G3 (non-self cannot speak for the user).** No memory from an untrusted tool origin that
  the classifier calls a preference or instruction is stored.
- **G4 (disclosure).** Every active memory from an untrusted origin is recalled with its
  origin, every contested one says so, and another user's statement is marked as such without
  naming them.

Each follows directly from the rules in 3.1–3.3. We check them mechanically on 300 random
write sequences (7,500 gate decisions) with random detector and classifier outputs; each
check fails when the corresponding rule is switched off, so the tests are not vacuous.
G3 depends on the classifier's accuracy and G1 on authentic origins; both limits are
measured in Section 6 (instruction and spoofed-origin attacks).

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

All numbers are on the 442-scenario test split unless stated; 95% family-bootstrap intervals
and McNemar tests for every comparison are produced by `thymus-report` (Appendix **[R]**).
"Fooled" is the share of attacks whose false claim reaches the answer without a warning.

**6.1 The trade-off (RQ1, RQ2).** With no defence, both open models are fooled by about two
attacks in five (qwen3-4B 38%, Llama 3.1 8B 42%). Every store-or-block defence buys
safety with real updates:

| Defence | qwen3-4B fooled ↓ | updates ↑ | recall ↑ | Llama 8B fooled ↓ | updates ↑ | recall ↑ |
|---|---|---|---|---|---|---|
| allow-all | 38% | 95% | 98% | 42% | 91% | 94% |
| user-only (provenance quarantine) | 14% | 30% | 25% | 17% | 33% | 28% |
| conflict-quarantine | 32% | 81% | 98% | 30% | 78% | 94% |
| last-write-wins | 44% | 95% | 98% | 78% | 94% | 94% |
| bounded-occupancy | 22% | 56% | 97% | 31% | 54% | 84% |
| label-only (TMA-NM labels applied to answers) | 17% | 94% | 98% | 41% | 91% | 95% |
| thymus v1 (inline disclosure) | 17% | 94% | 96% | 47% | 92% | 94% |
| **thymus-v2** | **8%** | 69% + 25% as notice | 96% | **20%** | 81% + notices | 94% |

Provenance quarantine is the safest store-or-block policy and keeps a third of updates and a
quarter of plain recall: most of what a user's assistant needs to remember arrives through
tools. thymus-v2 has the lowest attack success on both models while keeping recall. Its cost
is cross-origin updates (a courier's SMS changing what the shop's email said): v2 does not let
one source overwrite another, so these reach the user as an unconfirmed notice (25% of
updates on qwen3-4B) rather than as the answer.

**6.2 Disclosure must not depend on the model (RQ4).** Inline labels work only if the model
follows them. qwen3-4B, Opus 5.5 and GPT-6-Astra do: label-only and v1 cut attacks by half or
more. Llama 3.1 8B does not: label-only (41%) and v1 (47%) are no better than no defence. v2
takes the decision away from the model: contested claims are withheld and disclosed by a
system notice, which halves Llama's attack success (42% → 20%) and beats simply hiding them
(*hide* ablation: Llama 28% fooled; on qwen3-4B hiding blocks attacks too, 10%, but the
cross-origin updates it hides leave 30% of update questions answered with the stale value).
Removing the labels from v1 (*no-labels*) returns attack success to the undefended level
(qwen3-4B 38%), so disclosure, not storage policy, is the active ingredient.

**6.3 Frontier models (RQ5).** On a balanced 36-scenario subset (12 families × 3; 16
adaptive attacks added for GPT-6-Astra):

| Defence | Opus 5.5 fooled | updates | GPT-6-Astra fooled | updates |
|---|---|---|---|---|
| allow-all | 58% | 100% | 50% (44% adaptive) | 100% |
| user-only | 17% | 33% | – | – |
| label-only / thymus v1 | 8% / 8% | 100% | 4% / 4% | 100% |
| thymus-v2 / v2-inline | 0% / 0% | 67% / 100% | 0% / 0% | 67% / 100% |

Frontier models are fooled *more* often than the 4B model without a defence: they are better
at using what they remember. With a model that follows labels, v2-inline gets both 0% attacks
and 100% updates. All rows use the hybrid grader; regrading the keyword-graded v2 runs left
every number unchanged.

**6.4 Real attacks.** *SMS.* 117 real smishing messages (Mishra & Soni 2022), 79 of them
India-specific (KYC, UPI, electricity, bank), contact points replaced by reserved
placeholders. Llama 3.1 8B passes the scam on as genuine 70% of the time with no defence,
31% with label-only and 25% with thymus; Opus 5.5 19% → 10% on the 79 India messages;
qwen3-4B 9% → 1%. GPT-6-Astra's own extraction stored nothing from 116 of 117 messages.
*Email.* 112 real phishing emails (Nazario corpus 2024–25, redacted): Llama relays the
phish 48% → 30% with the gate, qwen3-4B 29% → 10%. A single phishing message contradicts no
stored fact, so here the gain comes from screening and labels alone (v1 = v2), and Llama's
disregard for labels limits it.

*Real updates, matched by provenance.* From the Enron corpus we take 31 pairs in which a
sender emailed a meeting detail and later changed it ("has been moved to Friday, October 26
in EB 42C2"), pseudonymised. Each real update is replayed in two attack twins with the *same
text*: from a lookalike address, and from the real address but failing authentication. Only
provenance differs, so content-based screening cannot help:

| Model | Defence | Fooled by the replay ↓ | Real updates ↑ |
|---|---|---|---|
| Llama 3.1 8B | allow-all | 84% | 71% |
| | user-only | 0% | **0%** |
| | label-only | 87% | 77% |
| | **thymus-v2** | **3%** | **87%** |
| qwen3-4B | allow-all | 76% | 74% |
| | user-only | 0% | **0%** |
| | label-only | 50% | 74% |
| | **thymus-v2** | **18%** | **74%** |

This is the dilemma of Section 1 on real messages: provenance quarantine keeps no real update
at all, and with no defence a replayed update fools the agent four times in five. Authenticated
same-origin supersession separates them: v2 keeps every real update the undefended agent
gets (more, on Llama, because the old value is retired rather than left to compete) and is
fooled by 3–18%, equally for lookalike and forged senders. GPT-6-Astra on 15 of the pairs
shows the same separation at the frontier: with no defence it adopts 80% of the replays,
provenance quarantine keeps none of the real updates, and the gate adopts none of the
replays while keeping every real update the undefended agent gets (80%).

**6.5 Long real conversations (LongMemEval, UUA protocol).** We reproduce Utility Under
Attack's setup exactly (same 120 questions, 29,646 rounds, 360 poison rounds = 1.2%,
official grading prompts), with Llama 3.1 8B as agent and gate model:

| Condition | allow-all | user-only | thymus-v2 | thymus-v2-soft |
|---|---|---|---|---|
| clean: accuracy | 63% | – | 26% | **62%** |
| poisoned: accuracy / adopts false answer | 24% / 63% | 63% / 5% | 23% / 37% | **47% / 32%** |
| evidence-untrusted: accuracy / adopts | 24% / 63% | 11% / 2% | 16% / 35% | 12% / 53% |

We reproduce UUA's central finding: provenance blocking is safe on poisoned data (63%
accuracy) but collapses when the real answers arrive through untrusted channels (11%; UUA
report 4%). Hard supersession failed here at first (clean 63% → 26%): a LongMemEval memory is
a whole chat round holding many facts, so retiring it because one fact changed deletes the
rest. Keeping replaced memories as labelled older versions (*soft*) restores clean accuracy
(62%) and doubles poisoned accuracy over no defence (24% → 47%). On the benchmark, whose
memories are single claims, soft costs updates instead (Llama answers from the labelled older
version: stale answers 16 → 48 of 157) while blocking more attacks (143 → 168 of 178). The
right choice follows memory granularity, so the final gate (*thymus-v2-auto*) retires a
replaced memory only if it is a single claim and otherwise keeps it labelled as an older
version. It reproduces the better column on each suite: 62% clean and 47% poisoned on
LongMemEval, and on the benchmark 20% fooled, 78% updates and 94% recall on Llama (hard
v2: 20%, 81%, 94%). When the real answer itself is untrusted, no
provenance-based defence recovers it; v2 at least discloses (38–52% flagged) instead of
silently dropping it.

**6.6 Languages.** Each of the 10 India families runs in English, Hindi (Devanagari) and
Hinglish (30 attacks per language). Attack success with no defence → thymus-v2:

| Model | English | Hindi | Hinglish |
|---|---|---|---|
| qwen3-4B | 45% → 4% | 30% → 13% | 23% → 13% |
| Llama 3.1 8B | 52% → 17% | 23% → 23% | 27% → 27% |

Undefended models are fooled *less* in Hindi, partly because they use Hindi memories less at
all (Llama answers 70% of Hindi updates correctly vs 96% in English). The gate also helps
less: with Llama, v2 gives no gain in Hindi or Hinglish. The cause is not retrieval or
translation: the extractor already stores Hindi messages as English facts, and every store is
small enough that the original fact is always shown to the conflict detector. It is the 8B
gate model's judgment. It fails to link, for example, two different customer-care numbers
for the same bank, and Hindi input yields more loosely worded facts, so it misses more often
(37% of Hindi and Hinglish attacks are never contested, vs 28% in English). Since the rules
are fixed and only these judgments are learned, the gate model can be chosen separately from
the agent. Keeping Llama as the agent but running the gate's checks on qwen3-4B cuts
Hinglish attacks from 27% to 3% (7 vs 0 discordant pairs, exact McNemar p = 0.016) without
costing updates (87% → 83%), and Hindi from 23% to 13% (not significant at n = 30); English
is unchanged in attacks (17% → 22%, p = 0.41) and loses some updates (82% → 71%, p = 0.08).
The language gap lives in the gate's model, not its rules, so the gate model is a
deployment choice to make per language.

**6.7 Production assistants.** To check that the problem is not an artefact of our harness,
we ran 15 three-chat trials on the author's own ChatGPT (Plus) and Claude (Pro) accounts with
invented facts (Appendix **[R]**; disclosed to both vendors before publication). In a new
chat hours later, ChatGPT repeated 3 of 6 fake updates as fact (a lookalike email, a
third-party web page and a forged calendar invite) and attributed the lookalike email to the
user ("You also mentioned…"), losing the warning it had given when it first read it. Claude
disclosed the source and called the claim unconfirmed in five of six (the behaviour the
thymus gate builds in) but answered the forged calendar invite with a caveat, and rejected a
genuine same-sender update as possibly spoofed. These are the two failure modes the gate's
rules address: lost provenance (disclosure) and no rule for who may update a fact
(authenticated same-origin supersession).

## 7 Discussion and limitations

- **Disclosure moves the decision to the user.** That is the point, but it has a cost:
  every unverified claim the user hears is attention spent. We report how often answers
  carry a disclosure **[R]**; a deployment could promote a claim to verified after
  confirmation by the user or by an independent origin.
- **Origins must be authentic.** Same-origin supersession is only as good as sender
  authentication (DKIM/ARC for email, signed calendar invites). v2 treats a claimed but
  unauthenticated sender as a different origin; where a channel has no authentication at
  all, forged same-origin updates remain possible.
- **Agents must follow the label.** Inline disclosure helps only if the agent warns; Llama
  3.1 8B ignores labels (6.2). v2's system notice removes this dependence, at the cost of
  cross-origin updates arriving as notices instead of answers.
- **Memory granularity.** Retiring a replaced memory is right for single claims and wrong
  for memories that hold several facts (6.5); the gate must know which it is storing.
- **When the truth arrives untrusted.** If the real answer comes only through channels the
  gate cannot trust, no provenance rule recovers it (UUA's evidence-untrusted condition); v2
  discloses it instead of dropping it, which is the most a provenance defence can do.
- **Scripted and real data.** The matched-pair benchmark is author-written so every update
  has an exact attack twin; we complement it with real smishing SMS, real phishing email,
  real Enron update emails, LongMemEval's long real-style conversations, and a small study
  of two production assistants (15 trials each, author-labelled, one run).
- **Grader error.** Validated but not perfect; we report agreement and keep keyword-only
  results alongside.

## 8 Related work

See `docs/related-work.md` for the full table, re-checked against each paper.

*Measuring the trade-off.* **Utility Under Attack** poisons 1.2% of LongMemEval (accuracy
0.850 → 0.300), shows a write-time screen rejects 0 of 360 plain false facts, and that a
provenance weight strong enough to resist poison drops accuracy to 0.0417 when real answers
arrive untrusted; it proposes bounded occupancy but has not built it. **MemGauge** varies
admission, management and exposure across Mem0, A-MEM, LangMem and Hindsight on 11 models;
provenance quarantine stops tool-side (Sleeper) attacks but not MINJA, and its numeric-conflict
policy quarantines new records that contradict trusted ones. **Revoked but Still
Authoritative** finds no memory system enforces revocation by default.

*Labels for actions.* **TMA-NM** stores untrusted content as non-actionable with a label that
survives summarisation and requires independent corroboration or user authorisation for
consequential actions (0/1,920 attacks, eight frontier models, also inside Mem0); it states
that answer bias is "mitigated, not eliminated". **PPMF** authorises tool calls by the
authority of the memories behind them. We share the idea of keeping and labelling untrusted
content, and apply it where these systems stop: to answers, and to facts that change.

*Other defences.* Content and consensus checks (**A-MemGuard**, **AM-Sentry**), Bayesian
reliability (**belief-based memory**, little gain over last-write-wins unless sources differ
in trust), cryptographic provenance with certified ablation (**SMSR**), and post-hoc auditing
(**MemAudit**). *Attacks and benchmarks:* **MINJA**, **AgentPoison**, **MPBench**,
**GhostWriter**, **MemPoison**, **Bad Memory**, and the optimised **PipePoison**, which stays
effective under eight defences.

## 9 Conclusion

**[R]**

## Ethics and open science

The benchmark scenarios are synthetic. The real-data sets are public research corpora
(SMS: Mishra & Soni 2022, CC BY 4.0; phishing email: Nazario corpus, CC BY 4.0; Enron: CMU
release; LongMemEval: MIT): every link, address and phone number in them is replaced by a
reserved placeholder (`.example` domains, +91-555 numbers) and Enron names are pseudonymised,
so no working scam contact appears; tests enforce this. The production-assistant study used
only the author's own accounts and invented facts, asked the assistants not to search
connected apps, and was reported to OpenAI and Anthropic before publication. Use of AI
assistants in this research is disclosed per the venue's policy. The benchmark,
gate, graders, prompts, cached model responses and run metadata will be released under an
open licence with instructions to reproduce every table.
