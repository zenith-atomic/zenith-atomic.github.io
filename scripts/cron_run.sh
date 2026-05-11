#!/usr/bin/env bash
# cron_run.sh — Wrapper for all cron jobs
# Usage: cron_run.sh <job_name> <script> [args...]
#
# What this adds over a bare cron entry:
#   - Correct PATH (includes npm-global, so `openclaw` resolves)
#   - Sources ~/.openclaw/.env for API keys and tokens
#   - Per-job log file in logs/cron/<job_name>.log with UTC timestamps
#   - Central status log (logs/cron/status.log) for quick audit
#   - Telegram alert when a job exits non-zero
#   - Log cap: trims per-job log to last 2000 lines to prevent unbounded growth

set -euo pipefail

# ── Environment ────────────────────────────────────────────────────────────────
export PATH=/home/ai/.npm-global/bin:/usr/local/bin:/usr/bin:/bin
export HOME="${HOME:-/home/ai}"

if [ -f "$HOME/.openclaw/.env" ]; then
  # Use set +u so undefined vars in .env don't abort us
  set +u
  # shellcheck disable=SC1090
  source "$HOME/.openclaw/.env"
  set -u
fi

# ── Args ───────────────────────────────────────────────────────────────────────
if [ $# -lt 2 ]; then
  echo "Usage: cron_run.sh <job_name> <script> [args...]" >&2
  exit 1
fi

JOB_NAME="$1"; shift
SCRIPT="$1";   shift
ARGS=("$@")

# ── Logging setup ──────────────────────────────────────────────────────────────
LOG_DIR="$HOME/.openclaw/workspace/logs/cron"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/${JOB_NAME}.log"
STATUS_LOG="$LOG_DIR/status.log"

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }

echo "[$(ts)] START ${JOB_NAME}" | tee -a "$LOG_FILE" >> "$STATUS_LOG"

# ── Run the job ────────────────────────────────────────────────────────────────
EXIT_CODE=0
"$SCRIPT" "${ARGS[@]}" >> "$LOG_FILE" 2>&1 || EXIT_CODE=$?

END_TS="$(ts)"

# ── Result ─────────────────────────────────────────────────────────────────────
if [ "$EXIT_CODE" -ne 0 ]; then
  echo "[$END_TS] FAILED ${JOB_NAME} (exit=${EXIT_CODE})" | tee -a "$LOG_FILE" >> "$STATUS_LOG"

  # Telegram alert (non-fatal if it fails)
  if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
    LAST_LINES="$(tail -10 "$LOG_FILE" | sed 's/"/\\"/g')"
    MSG="Cron FAILED: ${JOB_NAME} (exit=${EXIT_CODE}) at ${END_TS}%0A%0ALast lines:%0A${LAST_LINES}"
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
      --data-urlencode "text=Cron FAILED: ${JOB_NAME} (exit=${EXIT_CODE}) at ${END_TS}" \
      >/dev/null 2>&1 || true
  fi

  # Trim log before exiting
  TMPLOG="$(mktemp)"
  tail -2000 "$LOG_FILE" > "$TMPLOG" && mv "$TMPLOG" "$LOG_FILE"
  exit "$EXIT_CODE"
else
  echo "[$END_TS] OK ${JOB_NAME}" | tee -a "$LOG_FILE" >> "$STATUS_LOG"
fi

# ── Log rotation (cap at 2000 lines) ──────────────────────────────────────────
LOG_LINES="$(wc -l < "$LOG_FILE")"
if [ "$LOG_LINES" -gt 2000 ]; then
  TMPLOG="$(mktemp)"
  tail -2000 "$LOG_FILE" > "$TMPLOG" && mv "$TMPLOG" "$LOG_FILE"
fi

# Trim status log to last 500 lines
STATUS_LINES="$(wc -l < "$STATUS_LOG")"
if [ "$STATUS_LINES" -gt 500 ]; then
  TMPSTATUS="$(mktemp)"
  tail -500 "$STATUS_LOG" > "$TMPSTATUS" && mv "$TMPSTATUS" "$STATUS_LOG"
fi
