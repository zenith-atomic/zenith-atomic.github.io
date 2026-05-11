#!/usr/bin/env bash
set -euo pipefail

WORKDIR="/home/ai/.openclaw/workspace"
MEMORY_FILE="$WORKDIR/memory/MEMORY.md"
INBOX_FILE="$WORKDIR/memory/inbox.md"
RUNS_FILE="$WORKDIR/memory/agent_runs.md"

if [ "$#" -lt 1 ]; then
  echo 'usage: promote_fact.sh "durable fact sentence"' >&2
  exit 1
fi

FACT="$*"
DATE_UTC="$(date -u +%F)"
LINE="- $DATE_UTC — $FACT"

if grep -Fq "$FACT" "$MEMORY_FILE"; then
  echo "fact already present; no change"
  exit 0
fi

printf '%s\n' "$LINE" >> "$MEMORY_FILE"

TMP_FILE="$(mktemp)"
grep -Fv "$FACT" "$INBOX_FILE" > "$TMP_FILE" || true
mv "$TMP_FILE" "$INBOX_FILE"

printf '%s — promote_fact: %s — status: complete\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$FACT" >> "$RUNS_FILE"

"$WORKDIR/scripts/rotate_log.sh" "$RUNS_FILE" 50

echo "fact promoted"
