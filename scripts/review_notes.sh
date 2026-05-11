#!/usr/bin/env bash
set -euo pipefail

# Heuristic review: scan active_notes.log for promotion candidates
# and flag stale MEMORY.md entries.

WORKDIR="/home/ai/.openclaw/workspace"
NOTES="$WORKDIR/state/active_notes.log"
MEMORY="$WORKDIR/memory/MEMORY.md"

if [ ! -f "$NOTES" ]; then
  echo "No notes to review."
  exit 0
fi

# Count non-comment, non-empty lines
NOTE_COUNT="$(grep -cvE '^#|^$' "$NOTES" 2>/dev/null || echo 0)"
if [ "$NOTE_COUNT" -eq 0 ]; then
  echo "No notes to review."
  exit 0
fi

FOUND=0

# Surface candidates matching action keywords, excluding test entries
echo "=== Promotion candidates ==="
while IFS= read -r line; do
  # Extract the note text (last field after |)
  note="$(echo "$line" | awk -F'|' '{print $NF}' | sed 's/^ *//;s/ *$//')"
  [ -n "$note" ] || continue
  # Skip if already in MEMORY.md
  if grep -Fq "$note" "$MEMORY" 2>/dev/null; then
    continue
  fi
  echo "  -> $note"
  FOUND=1
done < <(grep -ivE '(^#|test|smoke|split test)' "$NOTES" | grep -iE '(decided|prefer|always|never|switched|deploy|upgrade|install|configur|using|goal|blocker|deadline|project|migrat|launch|ship|release|fix|broke|repair)')

if [ "$FOUND" -eq 0 ]; then
  echo "  (none found)"
fi

# Flag stale MEMORY.md entries older than 14 days
echo ""
echo "=== Stale entries (>14 days) ==="
CUTOFF="$(date -u -d '14 days ago' +%F)"
STALE=0
while IFS= read -r line; do
  DATE="$(echo "$line" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | head -1)"
  [ -n "$DATE" ] || continue
  if [[ "$DATE" < "$CUTOFF" ]]; then
    echo "  ? $line"
    STALE=1
  fi
done < <(grep -E '^- [0-9]{4}-[0-9]{2}-[0-9]{2}' "$MEMORY")

if [ "$STALE" -eq 0 ]; then
  echo "  (none)"
fi
