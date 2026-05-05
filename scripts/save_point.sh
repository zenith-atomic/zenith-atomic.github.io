#!/usr/bin/env bash
set -euo pipefail

WORKDIR="/home/ai/.openclaw/workspace"
TS_UTC="$(date -u +%Y%m%dT%H%M%S)"
BACKUP_ROOT="$WORKDIR/backups"
BACKUP_DIR="$BACKUP_ROOT/save_${TS_UTC}"
AGENT_RUNS="$WORKDIR/memory/agent_runs.md"
TMP_DIR="/tmp/openclaw-savepoint-${TS_UTC}-$$"

mkdir -p "$BACKUP_ROOT"
rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR"
trap 'rm -rf "$TMP_DIR"' EXIT

tar -C "$WORKDIR" --exclude='memory/snapshots' --exclude='./memory/snapshots' -cf - core memory state | tar -C "$TMP_DIR" -xf -

if [ ! -d "$TMP_DIR/core" ] || [ ! -d "$TMP_DIR/memory" ] || [ ! -d "$TMP_DIR/state" ] \
  || [ ! -f "$TMP_DIR/core/identity.md" ] || [ ! -f "$TMP_DIR/core/user.md" ] \
  || [ ! -f "$TMP_DIR/core/memory_policy.md" ] || [ ! -f "$TMP_DIR/memory/MEMORY.md" ] \
  || [ ! -f "$TMP_DIR/state/ACTIVE_CONTEXT.md" ]; then
  echo "ERROR: save point content verification failed — aborting" >&2
  exit 1
fi

trap - EXIT
mv "$TMP_DIR" "$BACKUP_DIR"

printf '%s — manual_save_point_created: %s — status: complete\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$BACKUP_DIR" >> "$AGENT_RUNS"

"$WORKDIR/scripts/rotate_log.sh" "$AGENT_RUNS" 50

echo "save point created: $BACKUP_DIR"

# Prune save points: drop anything older than 7 days AND enforce a max of 10 total, always keeping at least 1
MAX_SAVES=10
mapfile -t SAVES < <(ls -dt "$BACKUP_ROOT"/save_*/ 2>/dev/null)
CUTOFF="$(date -u -d '7 days ago' +%Y%m%dT%H%M%S)"
KEPT=0
for SAVE in "${SAVES[@]}"; do
  NAME="$(basename "$SAVE")"
  TS="${NAME#save_}"
  if ([ "$TS" \> "$CUTOFF" ] && [ "$KEPT" -lt "$MAX_SAVES" ]) || [ "$KEPT" -eq 0 ]; then
    KEPT=$((KEPT + 1))
  else
    rm -rf "$SAVE"
    printf '%s — save_point_pruned: %s — status: complete\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$SAVE" >> "$AGENT_RUNS"
  fi
done
