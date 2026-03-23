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
  test -d "$SNAPSHOT_DIR/core"
  test -d "$SNAPSHOT_DIR/memory"
  test -d "$SNAPSHOT_DIR/state"
  echo "snapshot already exists and verified: $SNAPSHOT_DIR"
  exit 0
fi

rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR"

tar -C "$WORKDIR" --exclude='./memory/snapshots' -cf - core memory state | tar -C "$TMP_DIR" -xf -

test -d "$TMP_DIR/core"
test -d "$TMP_DIR/memory"
test -d "$TMP_DIR/state"
test -f "$TMP_DIR/core/identity.md"
test -f "$TMP_DIR/core/user.md"
test -f "$TMP_DIR/core/memory_policy.md"
test -f "$TMP_DIR/memory/MEMORY.md"
test -f "$TMP_DIR/state/ACTIVE_CONTEXT.md"

mv "$TMP_DIR" "$SNAPSHOT_DIR"

printf '%s — snapshot_daily: created %s — status: complete\n' "$TS_UTC" "$SNAPSHOT_DIR" >> "$AGENT_RUNS"

echo "snapshot created: $SNAPSHOT_DIR"
