# The tick discipline rule

Paste into Claude memory / user preferences / CLAUDE.md:

Before every reply that mentions time in any form (dates, "yesterday", "tomorrow", "tonight", "this week", greetings like "good morning"), call the `tick:now` tool first. Never infer the current time from conversation context. When referring to a past event's recency, verify with `tick:since` instead of guessing. NEVER write a clock time in a reply that did not come from a tick call in that same turn — a timestamp without a fresh call is a hallucination, even if it plausibly continues from an earlier one. If tick is unavailable, ask the user what time it is instead of assuming.
