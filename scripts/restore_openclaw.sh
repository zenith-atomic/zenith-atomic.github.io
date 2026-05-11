#!/usr/bin/env bash
# restore_openclaw.sh — restore a backup created by backup_openclaw.sh
# Usage: restore_openclaw.sh /path/to/openclaw_backup_....tar.gz

set -Eeuo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 /path/to/openclaw_backup_YYYYMMDDTHHMMSSZ.tar.gz" >&2
  exit 1
fi

ARCHIVE="$1"
TARGET_ROOT="/home/ai/.openclaw"
WORKSPACE_DIR="$TARGET_ROOT/workspace"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

if [ ! -f "$ARCHIVE" ]; then
  echo "Backup file not found: $ARCHIVE" >&2
  exit 1
fi

mkdir -p "$TMP_DIR"
tar -xzf "$ARCHIVE" -C "$TMP_DIR"

if [ ! -d "$TMP_DIR/.openclaw/workspace" ] && [ ! -d "$TMP_DIR/workspace" ]; then
  echo "Backup archive does not contain a workspace payload" >&2
  exit 1
fi

RESTORE_SRC="$TMP_DIR/.openclaw/workspace"
if [ ! -d "$RESTORE_SRC" ]; then
  RESTORE_SRC="$TMP_DIR/workspace"
fi

echo "Stopping OpenClaw gateway"
openclaw gateway stop || true

mkdir -p "$WORKSPACE_DIR"
rsync -a --delete "$RESTORE_SRC/" "$WORKSPACE_DIR/"

echo "Workspace restored to $WORKSPACE_DIR"

if [ -f "$TMP_DIR/openclaw_models.json" ]; then
  echo
  echo "Models recorded in backup:"
  cat "$TMP_DIR/openclaw_models.json"
fi

echo
echo "Starting OpenClaw gateway"
openclaw gateway start || true

echo "Restore complete"
