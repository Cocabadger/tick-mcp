# tick

**An MCP time server that keeps your AI honest about time.**

Your AI assistant has no clock. It guesses time from context — and in long
chats it fails: calls a 10-minute-old message "yesterday", says "good night"
at 2 PM, plans "tomorrow" from a date three days stale. If you run multi-day
working sessions with Claude, you've seen it.

`tick` fixes it. Zero dependencies, one file per flavor:

| | Transport | For | File |
|---|---|---|---|
| **local** | stdio | Claude Desktop, Claude Code, any local MCP client | [`local/server.py`](local/server.py) |
| **remote** | Streamable HTTP | claude.ai (web / mobile) custom connectors, self-hosting | [`remote/server.py`](remote/server.py) |

## What it gives your assistant

- **`now`** — the real current date/time (any IANA timezone), with weekday.
- **`since`** — honest gap between a timestamp and now ("3h 42m ago") —
  the anti-"yesterday" tool.

Tool descriptions are written to *push* the model to check time before using
any relative time words. That's the point: not a clock the AI *may* look at —
a clock it's *told* to look at.

## "But Claude already knows the date"

It knows the date the session *started*. That's it. In a chat that runs for
hours or days, that stamp goes stale — and there is no time of day, no
weekday awareness mid-session, and no way to tell whether your last message
arrived 10 minutes or 10 hours ago. The model papers over all of that by
guessing. `tick` replaces the guess with a tool call.

## Install: local (recommended)

Requires Python 3.9+ (macOS has it). Put `local/server.py` anywhere, e.g.
`~/mcp/tick/server.py`.

### Claude Desktop

Add to `claude_desktop_config.json`
(macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "tick": {
      "command": "python3",
      "args": ["/Users/YOU/mcp/tick/server.py"]
    }
  }
}
```

Restart Claude Desktop. Done.

### Claude Code

```bash
claude mcp add tick -- python3 /Users/YOU/mcp/tick/server.py
```

(or `--scope user` to have it in every project)

### Any other MCP client

It's a standard stdio MCP server. Point your client at
`python3 /path/to/server.py`.

## Install: remote (for claude.ai web / mobile)

claude.ai can't run local servers — it connects to remote MCP servers by URL.
Deploy your own instance in a couple of minutes; `remote/` ships a Dockerfile
that runs anywhere (Railway, Render, Fly.io, a VPS):

```bash
# Railway
railway init && railway up
```

Then in claude.ai: **Settings → Connectors → Add custom connector** and paste
`https://your-app.up.railway.app/mcp`.

Claude Code can use it too:

```bash
claude mcp add --transport http tick https://your-app.up.railway.app/mcp
```

**Timezone caveat:** a remote server doesn't know your local time. It defaults
to UTC (override with the `TICK_DEFAULT_TZ` env var), and the tool description
tells the model to always pass your IANA timezone. If you want a clock that
just knows your local time — run the local flavor.

## The discipline rule (the other half of the fix)

The server alone isn't enough — the model must be *required* to use it.
Add this to your Claude memory / user preferences / `CLAUDE.md`:

> Before every reply that mentions time in any form (dates, "yesterday",
> "tomorrow", "tonight", "this week", greetings like "good morning"),
> call the `tick:now` tool first. Never infer the current time from
> conversation context. When referring to a past event's recency, verify
> with `tick:since` instead of guessing.

Server + rule = an assistant that stops gaslighting you about what day it is.

## Why not just use the reference time server?

Anthropic's reference `mcp-server-time` exists and is fine. `tick` differs in
intent: single copy-pasteable file (no pip install), a `since` tool for
recency checks, a remote flavor for claude.ai web, and tool descriptions
engineered to *enforce* checking — plus the memory rule that makes it stick.
It's a behavior fix, not just an API.

## License

MIT. Do whatever.
