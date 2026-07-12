# tick hook — stamp every message with real send time (Claude Code)

MCP has a blind spot `tick` can't fix from inside: **user messages carry no
timestamps.** The model never knows when you sent a message — it can only
bracket it between `now` calls. And the model can skip the call and
hallucinate a plausible-looking stamp.

Claude Code has a systemic fix: hooks. A `UserPromptSubmit` hook runs on
every message you send, and its output is injected into the model's context.
So three lines of config stamp every one of your messages with the real
wall-clock send time — no tool call, nothing the model can skip:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "date '+[message sent: %A %Y-%m-%d %H:%M:%S %Z]'"
          }
        ]
      }
    ]
  }
}
```

Merge this into `~/.claude/settings.json` (global) or
`.claude/settings.json` (per project). Restart the session or open `/hooks`
once so it picks up the change.

From then on the model sees, next to each of your messages:

```
[message sent: Saturday 2026-07-11 21:46:50 CEST]
```

Use it together with the tick server: the hook stamps *your* messages,
`now`/`since` give the model a clock for everything else.

Claude Desktop and claude.ai have no hooks — there the discipline rule in
[`../RULE.md`](../RULE.md) is as far as enforcement goes.

Credit: [Ted Murray arrived at this pattern independently](https://dev.to/tadmstr/claude-code-doesnt-know-youve-been-gone-heres-the-fix-17ko)
before this repo existed — his write-up is a good read on the "you've been
gone" problem.
