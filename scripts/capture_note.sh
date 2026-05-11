#!/usr/bin/env bash
set -euo pipefail

WORKDIR="/home/ai/.openclaw/workspace"
LOG_FILE="$WORKDIR/state/active_notes.log"

if [ "$#" -lt 1 ]; then
  echo 'usage: capture_note.sh "text of note"' >&2
  exit 1
fi

NOTE="$*"
LOCAL_TS="$(TZ='America/New_York' date '+%Y-%m-%d %H:%M:%S %Z')"
UTC_TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf '%s | %s | %s\n' "$LOCAL_TS" "$UTC_TS" "$NOTE" >> "$LOG_FILE"

"$WORKDIR/scripts/rotate_log.sh" "$LOG_FILE" 100

echo "note captured"
