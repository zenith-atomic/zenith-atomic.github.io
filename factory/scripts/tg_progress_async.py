"""
Telegram progress bar module — asynchronous (stdlib only, no external deps).

Uses asyncio.to_thread + urllib.request so it works on any Python 3.9+ install
without pip packages. The thread pool keeps the event loop unblocked while the
HTTP POST runs, matching the semantics of aiohttp/httpx for this use case.

Usage:
    from tg_progress_async import send_progress_message, update_progress
"""

import asyncio
import json
import logging
import urllib.error
import urllib.request
from json import JSONDecodeError
from typing import Optional

logger = logging.getLogger(__name__)

# Per-message-id async locks to prevent concurrent edits.
_locks: dict[int, asyncio.Lock] = {}
_locks_mutex = asyncio.Lock()

# Per-message-id last-update timestamps for time throttling.
_last_update: dict[int, float] = {}


async def _get_lock(message_id: int) -> asyncio.Lock:
    async with _locks_mutex:
        if message_id not in _locks:
            _locks[message_id] = asyncio.Lock()
        return _locks[message_id]


# ---------------------------------------------------------------------------
# Transport layer
# ---------------------------------------------------------------------------

def _post_sync(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    """Blocking HTTP POST — called via asyncio.to_thread. Returns JSON or None."""
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        try:
            return json.loads(exc.read())
        except (JSONDecodeError, Exception):
            logger.warning("Telegram HTTP error %d: %s", exc.code, exc.reason)
    except urllib.error.URLError as exc:
        logger.warning("Telegram connection error: %s", exc.reason)
    except TimeoutError:
        logger.warning("Telegram request timed out: %s", url)
    except JSONDecodeError as exc:
        logger.warning("Telegram response not valid JSON: %s", exc)
    return None


async def _post(url: str, payload: dict) -> Optional[dict]:
    """Non-blocking async POST — runs _post_sync in the default thread pool."""
    return await asyncio.to_thread(_post_sync, url, payload)


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def get_progress_bar(current: int, total: int, bar_length: int = 10) -> str:
    """
    Returns a fixed-width progress bar string, e.g. '[████░░░░░░]'.
    Handles total==0, negative inputs, and current>total safely.
    """
    if total <= 0 or current <= 0:
        filled = 0
    else:
        filled = min(bar_length, round(bar_length * current / total))
    empty = bar_length - filled
    return "[" + "█" * filled + "░" * empty + "]"


def _build_text(current: int, total: int, stage: str, bar_length: int) -> str:
    bar = get_progress_bar(current, total, bar_length)
    if total <= 0 or current <= 0:
        pct = 0
    else:
        pct = min(100, round(100 * current / total))
    pct_str = f"{pct:3d}%"
    suffix = f"  {stage}" if stage else ""
    return f"<code>{bar} {pct_str}{suffix}</code>"


async def send_progress_message(token: str, chat_id: str, text: str = "Starting...") -> Optional[int]:
    """
    Sends an initial message and returns message_id.
    Returns None if the API call fails.
    """
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": f"<code>{text}</code>",
        "parse_mode": "HTML",
    }
    for attempt in range(3):
        data = await _post(url, payload)
        if data and data.get("ok"):
            return data["result"]["message_id"]
        if data and data.get("error_code") == 429:
            retry_after = data.get("parameters", {}).get("retry_after", 5)
            logger.warning("Rate limited, waiting %ds", retry_after)
            await asyncio.sleep(retry_after)
            continue
        if attempt < 2:
            await asyncio.sleep(2 ** attempt)
    logger.error("Failed to send initial Telegram message after 3 attempts")
    return None


async def _edit_message(token: str, chat_id: str, message_id: int, text: str) -> bool:
    """
    Edits an existing Telegram message. Retries up to 3x with exponential backoff.
    Async-safe per message_id via asyncio.Lock. Returns True on success.
    """
    url = f"https://api.telegram.org/bot{token}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
    }
    lock = await _get_lock(message_id)
    async with lock:
        for attempt in range(3):
            data = await _post(url, payload)
            if data and data.get("ok"):
                return True
            if data and data.get("error_code") == 429:
                retry_after = data.get("parameters", {}).get("retry_after", 5)
                logger.warning("Rate limited on edit, waiting %ds", retry_after)
                await asyncio.sleep(retry_after)
                continue
            if data and not data.get("ok"):
                desc = data.get("description", "unknown error")
                if "message is not modified" in desc:
                    return True
                logger.warning("editMessageText failed: %s", desc)
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
    logger.error("Failed to edit Telegram message %d after 3 attempts", message_id)
    return False


async def update_progress(
    token: str,
    chat_id: str,
    message_id: Optional[int],
    current: int,
    total: int,
    last_pct: int,
    last_stage: str = "",
    stage: str = "",
    bar_length: int = 10,
    min_interval: float = 1.0,
) -> tuple[int, str]:
    """
    Sends an editMessageText update only when progress has meaningfully changed.

    Gate conditions (any one triggers an update):
      - Integer percentage increased
      - Stage string changed

    Time throttle: skips update if < min_interval seconds since last update.

    Returns (new_pct, stage) — always safe to store as the new last_* values.
    """
    if message_id is None:
        return last_pct, last_stage

    current = max(0, current)
    total = max(0, total)
    current = min(current, total) if total > 0 else 0

    new_pct = min(100, round(100 * current / total)) if total > 0 else 0

    pct_changed = new_pct != last_pct
    stage_changed = stage != last_stage

    if not pct_changed and not stage_changed:
        return last_pct, last_stage

    now = asyncio.get_event_loop().time()
    if not stage_changed and min_interval > 0:
        last_ts = _last_update.get(message_id, 0.0)
        if now - last_ts < min_interval:
            return last_pct, last_stage

    text = _build_text(current, total, stage, bar_length)
    if await _edit_message(token, chat_id, message_id, text):
        _last_update[message_id] = now

    return new_pct, stage


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------

async def _demo(token: str, chat_id: str) -> None:
    import asyncio as _asyncio

    # --- Mode A: Deterministic loop ---
    print("Running deterministic loop demo (100 items)...")
    msg_id = await send_progress_message(token, chat_id, "Processing items...")
    last_pct, last_stage = -1, ""
    for i in range(100):
        await _asyncio.sleep(0.05)
        last_pct, last_stage = await update_progress(
            token, chat_id, msg_id,
            current=i + 1, total=100,
            last_pct=last_pct, last_stage=last_stage,
            min_interval=1.0,
        )
    await update_progress(token, chat_id, msg_id, 100, 100, -1, stage="complete")
    print(f"Done. Final message_id={msg_id}")

    # --- Mode B: Stage-based ---
    STAGES = ["queued", "started", "fetching", "analyzing", "writing", "complete"]
    print("\nRunning stage-based demo...")
    msg_id2 = await send_progress_message(token, chat_id, "Starting agent...")
    last_pct, last_stage = -1, ""
    for idx, stage in enumerate(STAGES):
        await _asyncio.sleep(0.8)
        last_pct, last_stage = await update_progress(
            token, chat_id, msg_id2,
            current=idx + 1, total=len(STAGES),
            last_pct=last_pct, last_stage=last_stage,
            stage=stage,
            min_interval=0.0,
        )
    print(f"Done. Final message_id={msg_id2}")

    # --- Edge case checks ---
    print("\nEdge case checks:")
    print(repr(get_progress_bar(0, 0)))
    print(repr(get_progress_bar(-5, 10)))
    print(repr(get_progress_bar(12, 10)))
    print(repr(get_progress_bar(5, 10)))


if __name__ == "__main__":
    import os

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
    CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

    asyncio.run(_demo(TOKEN, CHAT_ID))
