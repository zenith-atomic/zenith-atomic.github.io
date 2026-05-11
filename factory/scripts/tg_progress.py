"""
Telegram progress bar module — synchronous (requests).

Usage:
    from tg_progress import send_progress_message, update_progress

Credentials: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID from env or passed directly.
"""

import logging
import threading
import time
from json import JSONDecodeError
from typing import Optional

import requests
from requests.exceptions import ConnectionError, Timeout

logger = logging.getLogger(__name__)

# Per-message-id locks to prevent concurrent edits to the same message.
_locks: dict[int, threading.Lock] = {}
_locks_mutex = threading.Lock()

# Per-message-id last-update timestamps for time throttling.
_last_update: dict[int, float] = {}


def _get_lock(message_id: int) -> threading.Lock:
    with _locks_mutex:
        if message_id not in _locks:
            _locks[message_id] = threading.Lock()
        return _locks[message_id]


# ---------------------------------------------------------------------------
# Transport layer
# ---------------------------------------------------------------------------

def _post(url: str, payload: dict, timeout: int = 10) -> Optional[dict]:
    """Single HTTP POST to Telegram API. Returns parsed JSON or None."""
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        return resp.json()
    except Timeout:
        logger.warning("Telegram request timed out: %s", url)
    except ConnectionError as exc:
        logger.warning("Telegram connection error: %s", exc)
    except JSONDecodeError as exc:
        logger.warning("Telegram response not valid JSON: %s", exc)
    return None


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
    """Assembles the final HTML-wrapped progress message."""
    bar = get_progress_bar(current, total, bar_length)
    if total <= 0 or current <= 0:
        pct = 0
    else:
        pct = min(100, round(100 * current / total))
    pct_str = f"{pct:3d}%"
    suffix = f"  {stage}" if stage else ""
    return f"<code>{bar} {pct_str}{suffix}</code>"


def send_progress_message(token: str, chat_id: str, text: str = "Starting...") -> Optional[int]:
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
        data = _post(url, payload)
        if data and data.get("ok"):
            return data["result"]["message_id"]
        if data and data.get("error_code") == 429:
            retry_after = data.get("parameters", {}).get("retry_after", 5)
            logger.warning("Rate limited, waiting %ds", retry_after)
            time.sleep(retry_after)
            continue
        if attempt < 2:
            time.sleep(2 ** attempt)
    logger.error("Failed to send initial Telegram message after 3 attempts")
    return None


def _edit_message(token: str, chat_id: str, message_id: int, text: str) -> bool:
    """
    Edits an existing Telegram message. Retries up to 3x with exponential backoff.
    Thread-safe per message_id. Returns True on success.
    """
    url = f"https://api.telegram.org/bot{token}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
    }
    lock = _get_lock(message_id)
    with lock:
        for attempt in range(3):
            data = _post(url, payload)
            if data and data.get("ok"):
                return True
            if data and data.get("error_code") == 429:
                retry_after = data.get("parameters", {}).get("retry_after", 5)
                logger.warning("Rate limited on edit, waiting %ds", retry_after)
                time.sleep(retry_after)
                continue
            if data and not data.get("ok"):
                desc = data.get("description", "unknown error")
                # "message is not modified" is not a real error — skip silently.
                if "message is not modified" in desc:
                    return True
                logger.warning("editMessageText failed: %s", desc)
            if attempt < 2:
                time.sleep(2 ** attempt)
    logger.error("Failed to edit Telegram message %d after 3 attempts", message_id)
    return False


def update_progress(
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

    # Clamp inputs.
    current = max(0, current)
    total = max(0, total)
    current = min(current, total) if total > 0 else 0

    new_pct = min(100, round(100 * current / total)) if total > 0 else 0

    pct_changed = new_pct != last_pct
    stage_changed = stage != last_stage

    if not pct_changed and not stage_changed:
        return last_pct, last_stage

    # Time throttle (skip if updated too recently), unless stage changed.
    now = time.monotonic()
    if not stage_changed and min_interval > 0:
        last_ts = _last_update.get(message_id, 0.0)
        if now - last_ts < min_interval:
            return last_pct, last_stage

    text = _build_text(current, total, stage, bar_length)
    if _edit_message(token, chat_id, message_id, text):
        _last_update[message_id] = now

    return new_pct, stage


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
    CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

    # --- Mode A: Deterministic loop ---
    print("Running deterministic loop demo (100 items)...")
    msg_id = send_progress_message(TOKEN, CHAT_ID, "Processing items...")
    last_pct, last_stage = -1, ""
    items = list(range(100))
    for i, _ in enumerate(items):
        time.sleep(0.05)  # simulate work
        last_pct, last_stage = update_progress(
            TOKEN, CHAT_ID, msg_id,
            current=i + 1, total=len(items),
            last_pct=last_pct, last_stage=last_stage,
            min_interval=1.0,
        )
    update_progress(TOKEN, CHAT_ID, msg_id, 100, 100, -1, stage="complete")
    print(f"Done. Final message_id={msg_id}")

    # --- Mode B: Stage-based ---
    STAGES = ["queued", "started", "fetching", "analyzing", "writing", "complete"]
    print("\nRunning stage-based demo...")
    msg_id2 = send_progress_message(TOKEN, CHAT_ID, "Starting agent...")
    last_pct, last_stage = -1, ""
    for idx, stage in enumerate(STAGES):
        time.sleep(0.8)  # simulate agent work per stage
        last_pct, last_stage = update_progress(
            TOKEN, CHAT_ID, msg_id2,
            current=idx + 1, total=len(STAGES),
            last_pct=last_pct, last_stage=last_stage,
            stage=stage,
            min_interval=0.0,  # always update on stage change
        )
    print(f"Done. Final message_id={msg_id2}")

    # --- Edge case checks (no network required) ---
    print("\nEdge case checks:")
    print(repr(get_progress_bar(0, 0)))      # all empty
    print(repr(get_progress_bar(-5, 10)))    # negative current
    print(repr(get_progress_bar(12, 10)))    # overflow
    print(repr(get_progress_bar(5, 10)))     # 50%
