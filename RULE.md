# The tick discipline rule

Paste into Claude memory / user preferences / CLAUDE.md:

Before every reply that mentions time in any form (dates, "yesterday", "tomorrow", "tonight", "this week", greetings like "good morning"), first call the `now` tool of the tick time server (it may be registered under any name — tick, tick-mcp, whatever the connector is called). Never infer the current time from conversation context. When referring to a past event's recency, verify with the `since` tool instead of guessing. NEVER write a clock time in a reply that did not come from a tick call in that same turn — a timestamp without a fresh call is a hallucination, even if it plausibly continues from an earlier one. If the tools are unavailable, ask the user what time it is instead of assuming.
