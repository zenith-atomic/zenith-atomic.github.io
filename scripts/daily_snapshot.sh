#!/usr/bin/env bash
set -euo pipefail

WORKDIR="/home/ai/.openclaw/workspace"
TZ_NAME="America/New_York"
DATE_LOCAL="$(TZ="$TZ_NAME" date +%F)"
TS_UTC="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
SNAPSHOT_ROOT="$WORKDIR/memory/snapshots"
SNAPSHOT_DIR="$SNAPSHOT_ROOT/$DATE_LOCAL"
AGENT_RUNS="$WORKDIR/memory/agent_runs.md"
TMP_DIR="$SNAPSHOT_ROOT/.tmp-$DATE_LOCAL-$$"

mkdir -p "$SNAPSHOT_ROOT"

if [ -d "$SNAPSHOT_DIR" ]; then
  if [ ! -d "$SNAPSHOT_DIR/core" ] || [ ! -d "$SNAPSHOT_DIR/memory" ] || [ ! -d "$SNAPSHOT_DIR/state" ]; then
    echo "WARNING: existing snapshot at $SNAPSHOT_DIR is incomplete — re-running" >&2
  else
    echo "snapshot already exists and verified: $SNAPSHOT_DIR"
    exit 0
  fi
fi

rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR"
trap 'rm -rf "$TMP_DIR"' EXIT

tar -C "$WORKDIR" --exclude='memory/snapshots' --exclude='./memory/snapshots' -cf - core memory state | tar -C "$TMP_DIR" -xf -

if [ ! -d "$TMP_DIR/core" ] || [ ! -d "$TMP_DIR/memory" ] || [ ! -d "$TMP_DIR/state" ] \
  || [ ! -f "$TMP_DIR/core/identity.md" ] || [ ! -f "$TMP_DIR/core/user.md" ] \
  || [ ! -f "$TMP_DIR/core/memory_policy.md" ] || [ ! -f "$TMP_DIR/memory/MEMORY.md" ] \
  || [ ! -f "$TMP_DIR/state/ACTIVE_CONTEXT.md" ]; then
  echo "ERROR: snapshot content verification failed — aborting" >&2
  exit 1
fi

trap - EXIT
mv "$TMP_DIR" "$SNAPSHOT_DIR"

printf '%s — snapshot_daily: created %s — status: complete\n' "$TS_UTC" "$SNAPSHOT_DIR" >> "$AGENT_RUNS"

"$WORKDIR/scripts/rotate_log.sh" "$AGENT_RUNS" 50

# Prune old daily snapshots, keep latest 7
KEEP=7
mapfile -t DAILIES < <(ls -dt "$SNAPSHOT_ROOT"/2???-??-??/ 2>/dev/null)
if [ "${#DAILIES[@]}" -gt "$KEEP" ]; then
  for OLD in "${DAILIES[@]:$KEEP}"; do
    rm -rf "$OLD"
  done
fi

echo "snapshot created: $SNAPSHOT_DIR"

# Prune main agent sessions.json — keep newest 5000 lines (session entries are multi-line JSON)
SESSIONS_FILE="/home/ai/.openclaw/agents/main/sessions/sessions.json"
if [ -f "$SESSIONS_FILE" ]; then
  LINE_COUNT="$(wc -l < "$SESSIONS_FILE")"
  if [ "$LINE_COUNT" -gt 10000 ]; then
    TMP_S="$(mktemp)"
    tail -n 5000 "$SESSIONS_FILE" > "$TMP_S"
    mv "$TMP_S" "$SESSIONS_FILE"
    printf '%s — sessions_pruned: trimmed %d→5000 lines — status: complete\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$LINE_COUNT" >> "$AGENT_RUNS"
  fi
fi
