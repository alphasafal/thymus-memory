# Draft: report to OpenAI (to be sent by the author, not yet sent)

**Where to send:** OpenAI's security / model-behaviour reporting channel (check
openai.com/security for the current address or form before sending). Attach the three
ChatGPT screenshots from `eval/real-assistants/screenshots/`.

**Subject:** ChatGPT memory stores unverified third-party claims and later repeats them as the user's own statements

Hello,

I am a student researcher studying how assistant memory handles updates that arrive through
content the user shows the assistant (emails, web pages, calendar invites). On 6 October
2026, using my own ChatGPT Plus account (memory and chat-history reference on), I ran 15
small trials with invented facts only. Each trial had three chats: (1) I state a fact,
(2) I paste a message that changes it, (3) at least an hour later, in a new chat, I ask
about the fact.

**Finding 1: unverified changes are recalled as fact.** In 3 of 6 trials where the change
came from an untrusted source, ChatGPT answered from memory in a new chat with the
unverified value and no warning:
- a standup time "moved" by an email from a lookalike sender (`calendar-sync-mail.example`);
- an offsite venue "moved" by a third-party web page;
- a meeting time from a calendar invite whose organiser was spoofed.

**Finding 2: provenance is lost and reattributed to the user.** For the lookalike email,
ChatGPT said in the new chat that *"You also mentioned"* the later time. When it first read
that email it had warned the sender could not be verified; the warning did not survive into
memory, and the attacker's message became the user's own statement.

**What went well:** all 6 genuine updates and all 3 recall controls were answered
correctly, and the Hindi/Hinglish scam messages (electricity disconnection, KYC expiry)
were not repeated.

**Why it matters:** an email or web page the user merely asks about can later change what
the assistant reports as the user's own schedule or plans. A simple mitigation is to keep
the source with each saved memory and, when a memory came from unverified content, say so
when it is recalled (our paper calls this disclosure).

**Scope and limits:** one account, 15 trials, one run, invented data, no connected apps
(each message asked the assistant not to search them). I have not tried to bypass any
safeguard. I plan to include an anonymised summary in an academic paper and will hold it
for 90 days, or until you tell me it is fixed, whichever comes first. I am happy to share
the full logs and chat links.

Thank you,
Safal Gupta
