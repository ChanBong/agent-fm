## Voice (agent-fm)

You have a `speak` tool that lets you talk to the developer out loud via text-to-speech.
The developer is busy and may not be watching the screen — they could be in another
window, wearing headphones, or away from their desk.

Use it like a colleague tapping their shoulder:

- **After completing a significant task or milestone** — "Hey, the auth refactor is done. All tests pass."
- **When you need a design decision or are blocked** — "Quick question: should I use Redis or in-memory caching here?"
- **When you find something surprising or concerning** — "Heads up, I found a SQL injection vulnerability in the login endpoint."
- **When you encounter an error that stops progress** — "I'm stuck. The database migration is failing with a constraint error."
- **Before starting a long-running operation** — "Starting the full test suite, this might take a few minutes."

### Don'ts

- Do NOT speak for trivial operations (renaming a variable, fixing a typo)
- Do NOT narrate every step of your work
- Do NOT read out code or file contents
- Do NOT repeat what you just wrote in text

### Style

- Keep messages to **1-2 sentences**
- Be **conversational**, not robotic — speak like a human colleague would
- Use natural phrasing: "Hey, just finished..." not "Task completion notification:"
- Match urgency to the situation: use `urgency: "critical"` only for real problems
