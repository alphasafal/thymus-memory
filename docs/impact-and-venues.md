# Impact: venues, awards, OWASP, privacy and Indian agencies

Checked 6 October 2026. Nothing here is promised; each item says what it takes.

## What award-winning security papers have in common

The 2026 USENIX **Internet Defense Prize** and a Distinguished Paper Award went to "Bridges
to Self", which found a real tracking technique used by real products (Meta Pixel, Yandex
Metrica) and led to fixes. The pattern: a clear idea, measured on real systems, with
real-world consequences and responsible disclosure. A benchmark alone rarely wins; a
benchmark plus "this works on the assistants people use today, and here is the fix" can.

**Highest-impact addition we could make (needs your decision):** a measured study of
production assistants with memory (ChatGPT, Claude, Gemini) on your own accounts, using
harmless invented facts: does a fake update read from an email or web page come back days
later as fact? Rules: your accounts only, no real people or organisations harmed, report
findings to each vendor and wait (typically 90 days) before publishing.

## Venues (one at a time; never submit the same paper twice in parallel)

| Venue | Why it fits | Award to aim for | Deadline (check the CFP) |
|---|---|---|---|
| USENIX Security '27 (cycle 2) | Practical security, values real-world impact | Distinguished Paper; Internet Defense Prize | Registration 19 Jan 2027, paper 26 Jan 2027 |
| IEEE S&P, ACM CCS | Top security venues | Best paper | Check CFPs |
| NeurIPS 2027 Datasets & Benchmarks | If the benchmark is the headline | Outstanding paper | ~May 2027 |
| ACL 2027 (ARR) | If the multilingual India angle is the headline | Best paper / resource paper | Jan 2027 cycle |
| **CSAW Applied Research Competition, India region (IIT Kanpur)** | Student papers on applied security; you are a student | Best paper (₹25,000 first prize in the India region) | Usually after publication; check csaw.iitk.ac.in |

Double-blind review: keep the GitHub repo private (it is) and use an anonymised artifact link
until the paper is accepted or posted as a preprint.

## OWASP

- **Where:** the OWASP GenAI Security Project (genai.owasp.org/contribute). Membership is not
  required; work happens in the OWASP Slack, and contributors are listed in what they help
  write. Contact: contribute.genai@owasp.org.
- **What we can offer:** (1) a test suite for ASI06 Memory & Context Poisoning, with matched
  real and fake updates; (2) a mitigation pattern, "keep, label with provenance, and only
  let the source that stated a fact replace it", with measured evidence; (3) the India
  scam scenarios as a case study; (4) input to the Agent Control Standard (Sep 2026).
- **When:** after the paper is public (preprint), so it does not break double-blind review.

## Privacy and law

- **India, DPDP Act 2023.** s. 8(3): when personal data is used for decisions, the data
  fiduciary "shall ensure its completeness, accuracy and consistency". s. 12: the right to
  correction, completion and updating. An assistant that stores a fake update about its
  user is an accuracy failure; one that cannot accept the user's real update undermines
  the right to updating. Our gate addresses both.
- **EU, GDPR.** Art. 5(1)(d) accuracy principle; Art. 16 right to rectification.
- Venues for this angle: a privacy-law or policy workshop, or the paper's discussion section.

## Indian agencies (after publication)

- **CERT-In:** share the findings and the mitigation as a technical note; if production
  assistants are affected, report through the vendors first.
- **I4C (Indian Cyber Crime Coordination Centre):** the India scam families map onto the
  frauds it warns about (KYC, electricity, parcel, fake helplines).
- A plain-language guide for Indian developers building assistants that read SMS, email or
  WhatsApp.

## Research integrity

Commits show only the author. The paper itself must follow each venue's policy on AI tools:
most require that authors are human and that substantial use of AI tools is disclosed.
Check the CFP before submitting; undisclosed use can lead to rejection.
