#!/usr/bin/env python3
"""
tick (remote) — the same honest clock, served over Streamable HTTP.

Zero dependencies, one file. For claude.ai custom connectors (web/mobile)
and any remote MCP client. The local stdio flavor lives in ../local/.

A remote server does NOT know the user's local time. `now` defaults to UTC
(override with TICK_DEFAULT_TZ) and the tool description pushes the model
to always pass the user's IANA timezone.

Endpoint: POST /mcp   (GET / is a health check)
"""

import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    from zoneinfo import ZoneInfo  # stdlib, py3.9+
except ImportError:
    ZoneInfo = None

SERVER_NAME = "tick"
SERVER_VERSION = "1.0.0"
SUPPORTED_PROTOCOLS = {"2024-11-05", "2025-03-26", "2025-06-18"}
DEFAULT_TZ = os.environ.get("TICK_DEFAULT_TZ", "UTC")


def _tz(name: str):
    if ZoneInfo is None:
        raise ValueError("zoneinfo unavailable (Python < 3.9)")
    try:
        return ZoneInfo(name)
    except Exception:
        raise ValueError(f"unknown IANA timezone: {name!r}")


def tool_now(args: dict) -> str:
    tzname = args.get("timezone")
    try:
        tz = _tz(tzname or DEFAULT_TZ)
    except ValueError as e:
        return json.dumps({"error": str(e)})
    dt = datetime.now(tz)
    out = {
        "iso": dt.isoformat(timespec="seconds"),
        "weekday": dt.strftime("%A"),
        "date": dt.strftime("%Y-%m-%d"),
        "time": dt.strftime("%H:%M"),
        "timezone": str(dt.tzinfo),
        "human": dt.strftime("%A, %d %B %Y, %H:%M %Z"),
    }
    if not tzname:
        out["note"] = (
            f"no timezone given — this is {DEFAULT_TZ}, not the user's local time; "
            "pass the user's IANA timezone")
    return json.dumps(out, ensure_ascii=False)


def tool_since(args: dict) -> str:
    ts = args.get("timestamp", "")
    try:
        then = datetime.fromisoformat(ts)
    except (TypeError, ValueError):
        return json.dumps({"error": f"bad ISO timestamp: {ts!r}"})
    note = None
    if then.tzinfo is None:
        then = then.replace(tzinfo=_tz(DEFAULT_TZ))
        note = f"naive timestamp interpreted as {DEFAULT_TZ}; pass an offset for exact results"
    now = datetime.now(timezone.utc)
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
    out = {
        "human": f"{' '.join(parts)} {sign}",
        "days": d, "hours": h, "minutes": m,
        "direction": sign,
        "now": now.isoformat(timespec="seconds"),
    }
    if note:
        out["note"] = note
    return json.dumps(out, ensure_ascii=False)


TOOLS = [
    {
        "name": "now",
        "description": (
            "Get the REAL current date and time. Call this at the start of a reply "
            "and before using any relative time words (yesterday, tomorrow, tonight, "
            "next week). Never guess time from context. ALWAYS pass the user's IANA "
            "timezone — this server is remote, so without it you get UTC, not the "
            "user's local time."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "The user's IANA timezone, e.g. Europe/Warsaw. Omitting it returns UTC.",
                }
            },
        },
    },
    {
        "name": "since",
        "description": (
            "How long ago (or from now) a given ISO-8601 timestamp is, in human form "
            "('3h 42m ago'). Use to check whether an event was really 'yesterday'. "
            "Include the UTC offset in the timestamp."
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
        proto = (req.get("params") or {}).get("protocolVersion")
        if proto not in SUPPORTED_PROTOCOLS:
            proto = "2025-03-26"
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": proto,
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


def _safe_handle(msg: dict) -> dict | None:
    try:
        return handle(msg)
    except Exception as e:
        rid = msg.get("id")
        if rid is None:
            return None
        return {"jsonrpc": "2.0", "id": rid,
                "error": {"code": -32603, "message": f"internal error: {e}"}}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, code: int, body: bytes = b"",
              ctype: str = "application/json"):
        self.send_response(code)
        if body:
            self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self):
        if self.path.rstrip("/") == "":
            self._send(200, json.dumps(
                {"status": "ok", "server": SERVER_NAME,
                 "version": SERVER_VERSION, "mcp_endpoint": "/mcp"}).encode())
        else:
            # no server-initiated SSE streams — allowed by the Streamable HTTP spec
            self._send(405)

    def do_OPTIONS(self):
        self._send(204)

    def do_DELETE(self):
        # stateless server: session termination is a no-op
        self._send(200)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length)
            msg = json.loads(raw)
        except (ValueError, json.JSONDecodeError):
            self._send(400, json.dumps(
                {"jsonrpc": "2.0", "id": None,
                 "error": {"code": -32700, "message": "parse error"}}).encode())
            return
        if isinstance(msg, list):  # JSON-RPC batch (protocol 2025-03-26)
            resps = [r for r in (_safe_handle(m) for m in msg if isinstance(m, dict))
                     if r is not None]
            if resps:
                self._send(200, json.dumps(resps).encode())
            else:
                self._send(202)
        elif isinstance(msg, dict):
            resp = _safe_handle(msg)
            if resp is not None:
                self._send(200, json.dumps(resp).encode())
            else:
                self._send(202)
        else:
            self._send(400, json.dumps(
                {"jsonrpc": "2.0", "id": None,
                 "error": {"code": -32600, "message": "invalid request"}}).encode())

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} {fmt % args}", flush=True)


def main():
    port = int(os.environ.get("PORT", 8787))
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"tick {SERVER_VERSION} listening on :{port} (MCP endpoint: /mcp)", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
