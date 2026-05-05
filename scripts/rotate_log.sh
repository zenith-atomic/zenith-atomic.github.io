#!/usr/bin/env bash
set -euo pipefail

# Rotate a log file to keep only the last N lines (plus header comments).
# Usage: rotate_log.sh <file> [max_lines]

LOG_FILE="$1"
MAX_LINES="${2:-50}"

[ -f "$LOG_FILE" ] || exit 0

CURRENT_LINES="$(wc -l < "$LOG_FILE")"
if [ "$CURRENT_LINES" -le "$MAX_LINES" ]; then
  exit 0
fi

# Preserve comment header lines (starting with #)
HEADER="$(grep '^#' "$LOG_FILE" || true)"
BODY_LINES=$((MAX_LINES - $(echo "$HEADER" | grep -c '^#' || echo 0)))
if [ "$BODY_LINES" -lt 1 ]; then
  BODY_LINES=1
fi

LOCK_FILE="${LOG_FILE}.lock"
(
  flock -x 200
  TMP="$(mktemp)"
  if [ -n "$HEADER" ]; then
    echo "$HEADER" > "$TMP"
  fi
  tail -n "$BODY_LINES" "$LOG_FILE" >> "$TMP"
  mv "$TMP" "$LOG_FILE"
) 200>"$LOCK_FILE"
