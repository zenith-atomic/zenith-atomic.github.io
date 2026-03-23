#!/usr/bin/env bash
set -euo pipefail

WORKDIR="/home/ai/.openclaw/workspace"
LOG_FILE="$WORKDIR/state/active_notes.log"

if [ "$#" -lt 1 ]; then
  echo "usage: capture_note.sh \"text of note\"" >&2
  exit 1
fi

NOTE="$*"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf '%s | %s\n' "$TS" "$NOTE" >> "$LOG_FILE"
