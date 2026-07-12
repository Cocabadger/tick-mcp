#!/usr/bin/env python3
"""
tick — MCP time server that keeps your AI honest about time.

Zero dependencies. One file. Gives Claude (Desktop, Code, any MCP client)
a real clock + drift guard so it stops saying "yesterday" about things
that happened 10 minutes ago.

Tools:
  now            — current local time (or any IANA timezone), with weekday
  since          — human gap between a given ISO timestamp and now
                   ("3h 42m ago") — the anti-"yesterday" tool
"""

import json
import sys
from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo  # stdlib, py3.9+
except ImportError:
    ZoneInfo = None

SERVER_NAME = "tick"
SERVER_VERSION = "1.1.0"


def _tz(name: str | None):
    if not name:
        return None  # server's local timezone
    if ZoneInfo is None:
        raise ValueError(
            "zoneinfo unavailable (Python < 3.9); omit 'timezone' to use local time")
    try:
        return ZoneInfo(name)
    except Exception:
        raise ValueError(f"unknown IANA timezone: {name!r}")


def tool_now(args: dict) -> str:
    try:
        tz = _tz(args.get("timezone"))
    except ValueError as e:
        return json.dumps({"error": str(e)})
    dt = datetime.now(tz) if tz else datetime.now().astimezone()
    return json.dumps({
        "iso": dt.isoformat(timespec="seconds"),
        "weekday": dt.strftime("%A"),
        "date": dt.strftime("%Y-%m-%d"),
        "time": dt.strftime("%H:%M"),
        "timezone": str(dt.tzinfo),
        "human": dt.strftime("%A, %d %B %Y, %H:%M %Z"),
    }, ensure_ascii=False)


def tool_since(args: dict) -> str:
    ts = args.get("timestamp", "")
    try:
        then = datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return json.dumps({"error": f"bad ISO timestamp: {ts!r}"})
    if then.tzinfo is None:
        then = then.astimezone()
    now = datetime.now(timezone.utc).astimezone()
    delta = now - then
    total = int(delta.total_seconds())
    sign = "ago" if total >= 0 else "from now"
    total = abs(total)
    d, rem = divmod(total, 86400)
    h, rem = divmod(rem, 3600)
    m, _ = divmod(rem, 60)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m or not parts: parts.append(f"{m}m")
    return json.dumps({
        "human": f"{' '.join(parts)} {sign}",
        "days": d, "hours": h, "minutes": m,
        "direction": sign,
        "now": now.isoformat(timespec="seconds"),
    }, ensure_ascii=False)


TOOLS = [
    {
        "name": "now",
        "description": (
            "Get the REAL current date and time. Call this at the start of a reply "
            "and before using any relative time words (yesterday, tomorrow, tonight, "
            "next week). Never guess time from context. NEVER write a clock time in "
            "your reply that did not come from this tool's output in THIS turn — a "
            "timestamp without a fresh call is a hallucination, even if it plausibly "
            "continues from an earlier one."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "IANA timezone, e.g. Europe/Warsaw. Omit for server's local time.",
                }
            },
        },
    },
    {
        "name": "since",
        "description": (
            "How long ago (or from now) a given ISO-8601 timestamp is, in human form "
            "('3h 42m ago'). Use to check whether an event was really 'yesterday'."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "timestamp": {"type": "string", "description": "ISO-8601, e.g. 2026-07-11T09:30:00+02:00"}
            },
            "required": ["timestamp"],
        },
    },
]


def handle(req: dict) -> dict | None:
    method = req.get("method")
    rid = req.get("id")

    if method == "initialize":
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        }}
    if method == "notifications/initialized":
        return None
    if method == "ping":
        return {"jsonrpc": "2.0", "id": rid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = req.get("params", {})
        name = params.get("name")
        args = params.get("arguments", {}) or {}
        fn = {"now": tool_now, "since": tool_since}.get(name)
        if fn is None:
            return {"jsonrpc": "2.0", "id": rid,
                    "error": {"code": -32601, "message": f"unknown tool {name}"}}
        try:
            text = fn(args)
            return {"jsonrpc": "2.0", "id": rid, "result": {
                "content": [{"type": "text", "text": text}]}}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": rid,
                    "error": {"code": -32000, "message": str(e)}}
    if rid is not None:
        return {"jsonrpc": "2.0", "id": rid,
                "error": {"code": -32601, "message": f"unknown method {method}"}}
    return None


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except (json.JSONDecodeError, RecursionError):
            continue
        # a malformed or unexpected message must never kill the server
        for msg in (req if isinstance(req, list) else [req]):
            if not isinstance(msg, dict):
                continue
            try:
                resp = handle(msg)
            except Exception as e:
                rid = msg.get("id")
                if rid is None:
                    continue
                resp = {"jsonrpc": "2.0", "id": rid,
                        "error": {"code": -32603, "message": f"internal error: {e}"}}
            if resp is not None:
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()


if __name__ == "__main__":
    main()
