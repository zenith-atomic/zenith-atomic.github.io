#!/usr/bin/env python3
"""
Claude Code hook handler — Telegram progress bar.

Registered for:
  PreToolUse(Agent)        track subagent start, show stage
  PostToolUse(Agent)       track subagent completion, advance progress
  PostToolUse(TodoWrite)   primary progress driver from task list
  Stop                     close out at "done" once pct reaches 100

State: /tmp/.tg_{session_id}.json  (expires after 24 h)
Must always exit 0 — never block Claude Code.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# ── env ──────────────────────────────────────────────────────────────────────
_env = Path.home() / ".openclaw" / ".env"
if _env.exists():
    for _ln in _env.read_text().splitlines():
        if "=" in _ln and not _ln.startswith("#"):
            _k, _, _v = _ln.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

TOKEN   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
BAR_LEN = 10
MIN_SEC = 2.0  # minimum seconds between Telegram edits (stage changes bypass this)


# ── state ────────────────────────────────────────────────────────────────────

def _state_path(sid: str) -> Path:
    return Path(f"/tmp/.tg_{sid}.json")


def _load(sid: str) -> dict:
    try:
        p = _state_path(sid)
        if p.exists():
            st = json.loads(p.read_text())
            if time.time() - st.get("created", 0) < 86400:
                return st
    except Exception:
        pass
    return {
        "msg_id": None,
        "last_pct": -1,
        "last_stage": "",
        "agents_started": 0,
        "agents_done": 0,
        "has_todos": False,
        "last_ts": 0.0,
        "created": time.time(),
    }


def _save(sid: str, st: dict) -> None:
    try:
        _state_path(sid).write_text(json.dumps(st))
    except Exception:
        pass


# ── transport ────────────────────────────────────────────────────────────────

def _tg(endpoint: str, payload: dict) -> dict | None:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/{endpoint}",
        data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read())
    except Exception:
        return None


# ── rendering ────────────────────────────────────────────────────────────────

def _bar(pct: int) -> str:
    filled = min(BAR_LEN, round(BAR_LEN * pct / 100))
    return "[" + "█" * filled + "░" * (BAR_LEN - filled) + "]"


def _render(pct: int, stage: str) -> str:
    suffix = f"  {stage}" if stage else ""
    return f"<code>{_bar(pct)} {pct:3d}%{suffix}</code>"


# ── Telegram ops ─────────────────────────────────────────────────────────────

def _send_new(text: str) -> int | None:
    data = _tg("sendMessage", {
        "chat_id": CHAT_ID, "text": text, "parse_mode": "HTML",
    })
    if data and data.get("ok"):
        return data["result"]["message_id"]
    return None


def _edit(msg_id: int, text: str) -> None:
    _tg("editMessageText", {
        "chat_id": CHAT_ID, "message_id": msg_id,
        "text": text, "parse_mode": "HTML",
    })
    # "message is not modified" is a benign Telegram error — ignored silently.


# ── update gate ──────────────────────────────────────────────────────────────

def _push(st: dict, pct: int, stage: str) -> None:
    """Gate redundant updates, then send or edit. Mutates st in-place."""
    now = time.monotonic()
    pct_changed   = pct   != st["last_pct"]
    stage_changed = stage != st["last_stage"]

    if not pct_changed and not stage_changed:
        return
    # Time-throttle pct-only updates; stage changes always go through.
    if not stage_changed and (now - st["last_ts"]) < MIN_SEC:
        return

    text = _render(pct, stage)
    if st["msg_id"] is None:
        st["msg_id"] = _send_new(text)
    else:
        _edit(st["msg_id"], text)

    st["last_pct"]   = pct
    st["last_stage"] = stage
    st["last_ts"]    = now


# ── progress helpers ─────────────────────────────────────────────────────────

def _todos_progress(todos: list) -> tuple[int, str]:
    """Derive (pct, stage) from a TodoWrite todos array."""
    if not todos:
        return 0, ""
    total = len(todos)
    done  = sum(1 for t in todos if t.get("status") == "completed")
    active = [t for t in todos if t.get("status") == "in_progress"]
    # Prefer activeForm (continuous tense) if present, fall back to content.
    if active:
        t = active[0]
        stage = (t.get("activeForm") or t.get("content", ""))[:28]
    else:
        stage = ""
    return min(100, round(100 * done / total)), stage


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    if not TOKEN or not CHAT_ID:
        return

    try:
        payload = json.load(sys.stdin)
    except Exception:
        return

    # Ignore hooks fired from inside subagents — only track the main session.
    if payload.get("agent_id"):
        return

    sid   = payload.get("session_id", "default")
    event = payload.get("hook_event_name", "")
    tool  = payload.get("tool_name", "")
    inp   = payload.get("tool_input", {})

    st = _load(sid)

    if event == "PreToolUse" and tool == "Agent":
        st["agents_started"] += 1
        desc = inp.get("description", "agent")[:25]
        # Keep current pct; update stage to show what's spinning up.
        _push(st, max(st["last_pct"], 0), f"→ {desc}")

    elif event == "PostToolUse" and tool == "Agent":
        st["agents_done"] += 1
        started = max(st["agents_started"], st["agents_done"])
        done    = st["agents_done"]
        desc    = inp.get("description", "agent")[:20]
        stage   = f"{done}/{started}  {desc}"

        if st["has_todos"]:
            # Todos drive pct; agents only provide stage context.
            _push(st, st["last_pct"], stage)
        else:
            # No todos — derive pct from agent completion ratio.
            agent_pct = min(100, round(100 * done / started))
            _push(st, agent_pct, stage)

    elif event == "PostToolUse" and tool == "TodoWrite":
        st["has_todos"] = True
        todos = inp.get("todos", [])
        pct, stage = _todos_progress(todos)
        _push(st, pct, stage)

    elif event == "Stop":
        # Stamp "done" only once when pct already reached 100.
        if st["msg_id"] and st["last_pct"] == 100 and st["last_stage"] != "done":
            _push(st, 100, "done")

    _save(sid, st)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # hooks must never crash Claude Code
    sys.exit(0)
