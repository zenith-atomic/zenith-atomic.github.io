#!/usr/bin/env bash
# backup_openclaw.sh — create a timestamped OpenClaw backup archive

set -Eeuo pipefail

DEST_DIR="${OPENCLAW_BACKUP_DIR:-/home/ai/backups/openclaw}"
RETENTION_DAYS="${OPENCLAW_BACKUP_RETENTION_DAYS:-7}"
TIMESTAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
BACKUP_NAME="openclaw_backup_${TIMESTAMP}.tar.gz"
WORKSPACE_DIR="/home/ai/.openclaw/workspace"
OPENCLAW_DIR="/home/ai/.openclaw"
TMP_DIR="$(mktemp -d)"
MODELS_JSON="$TMP_DIR/openclaw_models.json"
LOG_DIR="$WORKSPACE_DIR/logs"
LOG_FILE="$LOG_DIR/backup.log"
ARCHIVE_PATH="$DEST_DIR/$BACKUP_NAME"

log() {
  mkdir -p "$LOG_DIR"
  echo "$(date -u '+%Y-%m-%d %H:%M:%S') [backup] $1" | tee -a "$LOG_FILE"
}

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

mkdir -p "$DEST_DIR" "$LOG_DIR"

log "capturing installed models list"
if ! openclaw models list --json > "$MODELS_JSON" 2>/dev/null; then
  echo '[]' > "$MODELS_JSON"
fi

log "creating archive $ARCHIVE_PATH"
tar \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='__pycache__' \
  --exclude='logs/*.log.*' \
  -czf "$ARCHIVE_PATH" \
  -C /home/ai .openclaw/workspace \
  -C "$TMP_DIR" openclaw_models.json

if [ ! -s "$ARCHIVE_PATH" ]; then
  log "backup archive missing or empty"
  exit 1
fi

log "pruning backups older than $RETENTION_DAYS days"
find "$DEST_DIR" -maxdepth 1 -type f -name 'openclaw_backup_*.tar.gz' -mtime +"$RETENTION_DAYS" -delete

SIZE="$(du -h "$ARCHIVE_PATH" | awk '{print $1}')"
log "backup created: $ARCHIVE_PATH ($SIZE)"
printf '%s\n' "$ARCHIVE_PATH"
