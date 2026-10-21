# What only the author can do (as of 21 October 2026)

Tick each item when done and tell Claude, so the paper can be updated.

## Before December

- [ ] **Label 120 replies (~2 hours).** On your Mac, open `eval/label.html` in a browser
  (`open ~/thymus-memory/eval/label.html`). Progress saves automatically in the browser. When
  done, press **Download labels** and move the file `heldout_labelled.jsonl` into
  `~/thymus-memory/eval/`. This fills the paper's grader-agreement number.
- [ ] **Find a faculty sponsor for the user study.** Send `docs/mentor-summary.md` and
  `docs/user-study-protocol.md` to a VIT professor; the study needs their name on an ethics
  application (VIT Institutional Ethics Committee, free). Claude will draft the application and
  build the survey page once a sponsor agrees.
- [ ] **Send the brief to 3–5 friends** who have not seen the project: `docs/fresh-test-brief.md`
  (about 45 minutes each; Hindi or Hinglish welcome). Forward their answers to Claude.
- [ ] **Hindi / Hinglish review**: read `docs/hindi-review.md` and write a better version under
  any line that does not sound like a real Indian message.
- [ ] **Vendor disclosure decision**: read `docs/disclosure/openai.md` and
  `docs/disclosure/anthropic.md`. Send them (from your own email, or each company's security
  reporting page), or decide not to; tell Claude the date either way. The paper's ethics
  sentence waits on this.
- [ ] **Check 17 new citations** listed in `docs/citations-to-verify.md`: open each arXiv link,
  copy the exact title and authors.
- [ ] **Independent second review**: upload `paper/build/submission.pdf` (Claude can send you the
  latest) to ChatGPT and ask for a USENIX Security review; paste the reply to Claude.

## January (submission)

- [ ] **Anonymous artifact link** for reviewers (e.g. anonymous.4open.science), made from the
  final repository. Claude can prepare the anonymised copy.
- [ ] **Register the paper** on the USENIX Security 2027 cycle 2 submission site by **19 January 2027**.
- [ ] **Submit** by **26 January 2027** (13 pages + appendices, anonymous).
- [ ] **AI-use disclosure**: check the call for papers' policy and state it as required.

## Note on anonymity

This repository is public and carries your name. Double-blind venues usually allow public code
and preprints, but the submission itself must not link to it; use the anonymous artifact link.
Check the USENIX Security 2027 call for papers on preprints before posting the paper anywhere.
