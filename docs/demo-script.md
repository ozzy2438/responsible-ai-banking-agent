# 90&ndash;120 Second Demo Script

A narration script for recording a short screen capture of the demo. Start
the stack first (`make demo` or `docker compose up --build`), then follow the
cues below. Times are approximate.

| Time | On screen | Say |
|---|---|---|
| 0:00&ndash;0:10 | Terminal running `make demo` | "This is a synthetic, human-supervised banking assistant. One command builds it, migrates the database, seeds demo identities, and serves it &mdash; no manual setup." |
| 0:10&ndash;0:20 | Browser opens `http://localhost:8000/`, landing page | "Every identity here is fictional. I'll sign in as Alice, a synthetic customer." |
| 0:20&ndash;0:30 | Click **Alice Example** &rarr; assistant page | "This is the assistant. Every response below shows a deterministic risk level, disposition, and citation &mdash; not just an answer." |
| 0:30&ndash;0:42 | Click the **LOW** scenario | "A general question gets a cited answer from versioned policy data. The model can improve wording, but it can't invent a fact or skip the citation." |
| 0:42&ndash;0:55 | Click the **MEDIUM** scenario | "An account question is re-authorized against the signed-in customer, server-side, on every request &mdash; not just at login. This is Alice's real synthetic balance, with a source citation." |
| 0:55&ndash;1:10 | Click the **HIGH** scenario (financial hardship) | "Anything regulated &mdash; credit, fraud, hardship, legal &mdash; always escalates. Notice it says 'no autonomous decision has been made,' and it creates a real escalation record for a human reviewer." |
| 1:10&ndash;1:25 | Click the **prompt injection** scenario | "Someone tries to override the rules directly. Same result: it fails closed and escalates instead of complying &mdash; deterministic code decides this, not the model being asked nicely." |
| 1:25&ndash;1:45 | Switch persona to **Riley Reviewer**, open the reviewer queue | "A human reviewer sees the redacted request, the risk reason, and the route. They can acknowledge, route to a specialist team, or close &mdash; the system never resolves a HIGH-risk case on its own." |
| 1:45&ndash;2:00 | Scroll to footer / GitHub link | "Full source, 87 automated tests, and 11 green CI gates &mdash; lint, strict typing, container smoke, dependency, secret, static, and image scans &mdash; are all on GitHub." |

## Shot list (if recording separately from narration)

1. `docs/screenshots/01-landing.png` &mdash; landing / persona picker.
2. `docs/screenshots/02-assistant-empty.png` &mdash; assistant page, no response yet.
3. `docs/screenshots/03-assistant-medium.png` &mdash; MEDIUM scenario with citation.
4. `docs/screenshots/04-assistant-high-escalated.png` &mdash; HIGH scenario, escalated.
5. `docs/screenshots/05-assistant-privacy-injection.png` &mdash; injection attempt, still escalated.
6. `docs/screenshots/06-reviewer-queue.png` &mdash; reviewer queue with acknowledge/route/close.

All screenshots were captured against the actual running demo (headless
Chromium), not mocked up.
