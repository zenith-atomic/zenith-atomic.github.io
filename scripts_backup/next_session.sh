#!/usr/bin/env bash
set -euo pipefail

WORKDIR="/home/ai/.openclaw/workspace"
ACTIVE_FILE="$WORKDIR/state/ACTIVE_CONTEXT.md"
INBOX_FILE="$WORKDIR/memory/inbox.md"
NEXT_FILE="$WORKDIR/state/NEXT_SESSION.md"
RUNS_FILE="$WORKDIR/memory/agent_runs.md"

ACTIVE_FOCUS="$(awk '
  /^current_tasks:/ {in_tasks=1; next}
  in_tasks && /^open_loops:/ {in_tasks=0}
  in_tasks && /^  - / {sub(/^  - /, ""); print; exit}
' "$ACTIVE_FILE")"

if [ -z "$ACTIVE_FOCUS" ]; then
  ACTIVE_FOCUS="review active context and unresolved inbox items"
fi

OPEN_WORK="$(awk '
  /^- [0-9]{4}-[0-9]{2}-[0-9]{2} — candidate fact:/ {print}
' "$INBOX_FILE")"

if [ -z "$OPEN_WORK" ]; then
  OPEN_WORK="- no pending durable facts in inbox"
fi

cat > "$NEXT_FILE" <<EOF
# state/NEXT_SESSION.md

- active_focus: $ACTIVE_FOCUS
- open_work:
$OPEN_WORK
- first_checks:
  - read state/ACTIVE_CONTEXT.md
  - inspect memory/inbox.md
  - review memory/MEMORY.md before promoting new durable facts
EOF

printf '%s — next_session: regenerated state/NEXT_SESSION.md — status: complete\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$RUNS_FILE"
