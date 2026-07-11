# The tick discipline rule

Paste into Claude memory / user preferences / CLAUDE.md:

Before every reply that mentions time in any form (dates, "yesterday", "tomorrow", "tonight", "this week", greetings like "good morning"), call the `tick:now` tool first. Never infer the current time from conversation context. When referring to a past event's recency, verify with `tick:since` instead of guessing. If tick is unavailable, ask the user what time it is instead of assuming.
