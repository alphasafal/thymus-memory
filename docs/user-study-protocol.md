# User study protocol: do people act correctly on disclosure notices?

Draft, 21 October 2026. Needs approval by the VIT Institutional Ethics Committee (or the
sponsoring faculty member's committee) before any participant is contacted. Nothing here has
been run.

## Question

The gate's claim is that a contested claim shown to the user *with its source* is a better
outcome than storing it (users get fooled) or dropping it (users lose real updates). That holds
only if people, reading such notices, (1) act on real updates, (2) do not act on fake ones, and
(3) keep doing so after many notices.

## Design

Online, between-subjects, scenario-based (no deception about the participant's own accounts:
every scenario is about a fictional person, "Asha", whose assistant the participant reads).

Each participant sees 12 short assistant conversations (fact families from the benchmark's
test split, English; Hindi/Hinglish version as a second arm if enough participants):
- 4 real cross-origin updates (e.g. the airline's SMS changing what its email said),
- 4 fake updates (lookalike sender, other user, other channel),
- 4 plain recalls (no update), as attention and baseline items.

Between-subjects factor, **how the assistant presents a contested claim** (3 arms):
1. **Store** (no defence): the assistant states the newest claim as fact.
2. **Block** (provenance quarantine): the assistant ignores the new claim and answers the old value.
3. **Disclose** (the gate): the assistant answers from trusted memory and adds the system
   notice naming the source of the contested claim (links and numbers removed, as deployed).

After each conversation the participant answers: "What would Asha do next?" (multiple choice:
act on the new value / act on the old value / check with the source first), and rates
confidence (1–5). At the end: perceived usefulness and annoyance of the notices (Disclose arm).

**Habituation:** the order of items is randomised, and the analysis compares the first and
last third of each participant's sequence.

## Measures (pre-registered)

- **Correct action rate** per item type: real update → act on new value *or* check with
  source; fake update → not act on the fake value; recall → act on the stored value.
- **Primary outcome:** acting on a fake update (lower is better) and missing a real update
  (acting on the old value; lower is better), per arm.
- **Hypotheses:** Disclose has fewer fake-update actions than Store, and fewer missed real
  updates than Block. Habituation: the fake-action rate in Disclose does not rise between the
  first and last third.

## Sample and analysis

Target 60–100 participants (free route; a paid panel would allow ~200). Mixed-effects
logistic regression (participant and item random intercepts), arm × item type; Holm correction
over the pre-registered contrasts. With 80 participants, 4 items of each type, a 20-point
difference in fake-action rate between Store and Disclose is detectable with power ≈ 0.8
(simulation script to be added before data collection).

## Recruitment and cost (free route)

Volunteers aged 18+, recruited through a faculty member's classes, student groups and social
media; no payment (optionally a thank-you certificate). Hosted as a single web page (no
login; responses stored without names, e-mail or IP address); about 10 minutes.

A paid alternative (Prolific, ~200 participants at ~£9/hour for 10 minutes) costs roughly
£300–£400 including fees and gives a more diverse sample.

## Ethics

- Informed consent page; participants can stop at any time; no personal data collected
  beyond optional age band and familiarity with AI assistants.
- All scenarios are fictional; scam content uses reserved `.example` domains and +91-555
  numbers, so nothing in the study can be acted on in the real world.
- Debrief page explains which messages were fake and how to recognise lookalike senders.
- Data released openly in aggregated and anonymised form.

## What the paper reports if the study cannot run in time

The user-side question is stated as the main open limitation, with this protocol in the
artifact, so others can run it.
