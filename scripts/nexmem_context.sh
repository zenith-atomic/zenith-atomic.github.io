#!/usr/bin/env bash
set -euo pipefail

WORKDIR="/home/ai/.openclaw/workspace"
INBOX="$WORKDIR/memory/inbox.md"
MEMORY="$WORKDIR/memory/MEMORY.md"
ACTIVE="$WORKDIR/state/ACTIVE_CONTEXT.md"
NEXT="$WORKDIR/state/NEXT_SESSION.md"

printf '## NexMem Context\n\n'
printf '### Active context\n'
sed -n '1,120p' "$ACTIVE" | sed 's/^/- /'
printf '\n### Next session\n'
sed -n '1,80p' "$NEXT" | sed 's/^/- /'
printf '\n### Durable memory\n'
grep -E '^-' "$MEMORY" | tail -20 | sed 's/^/- /'
printf '\n### Inbox candidates\n'
grep -E '^-' "$INBOX" | tail -20 | sed 's/^/- /'
