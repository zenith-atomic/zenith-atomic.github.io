#!/usr/bin/env bash
set -euo pipefail

WORKDIR="/home/ai/.openclaw/workspace"
TS="$(date -u +%Y-%m-%dT%H-%M-%SZ)-$$"
SNAPSHOT_ROOT="$WORKDIR/memory/snapshots/quicksave"
SNAPSHOT_DIR="$SNAPSHOT_ROOT/$TS"
AGENT_RUNS="$WORKDIR/memory/agent_runs.md"
TMP_DIR="/tmp/openclaw-quicksave-$TS-$$"

rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR/core" "$TMP_DIR/memory" "$TMP_DIR/state" "$SNAPSHOT_ROOT"
trap 'rm -rf "$TMP_DIR"' EXIT

cp -R "$WORKDIR/core/." "$TMP_DIR/core/"
cp "$WORKDIR/memory/MEMORY.md" "$TMP_DIR/memory/"
cp "$WORKDIR/memory/inbox.md" "$TMP_DIR/memory/"
cp "$WORKDIR/memory/agent_runs.md" "$TMP_DIR/memory/"
cp -R "$WORKDIR/state/." "$TMP_DIR/state/"

if [ ! -d "$TMP_DIR/core" ] || [ ! -d "$TMP_DIR/memory" ] || [ ! -d "$TMP_DIR/state" ] \
  || [ ! -f "$TMP_DIR/core/identity.md" ] || [ ! -f "$TMP_DIR/core/user.md" ] \
  || [ ! -f "$TMP_DIR/core/memory_policy.md" ] || [ ! -f "$TMP_DIR/memory/MEMORY.md" ] \
  || [ ! -f "$TMP_DIR/state/ACTIVE_CONTEXT.md" ]; then
  echo "ERROR: quicksave content verification failed — aborting" >&2
  exit 1
fi

trap - EXIT
mv "$TMP_DIR" "$SNAPSHOT_DIR"

printf '%s — quicksave: created %s — status: complete\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$SNAPSHOT_DIR" >> "$AGENT_RUNS"

"$WORKDIR/scripts/rotate_log.sh" "$AGENT_RUNS" 50

# Prune old quicksaves, keep latest 5
KEEP=5
mapfile -t QUICKSAVES < <(ls -dt "$SNAPSHOT_ROOT"/*/ 2>/dev/null)
if [ "${#QUICKSAVES[@]}" -gt "$KEEP" ]; then
  for OLD in "${QUICKSAVES[@]:$KEEP}"; do
    rm -rf "$OLD"
  done
fi

echo "quicksave created: $SNAPSHOT_DIR"
