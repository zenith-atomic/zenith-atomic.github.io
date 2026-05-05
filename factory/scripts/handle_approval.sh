#!/usr/bin/env bash
set -euo pipefail

FACTORY="$HOME/.openclaw/workspace/factory"
QUEUE="$FACTORY/queue"
POST_SCRIPTS="$FACTORY/scripts/post"

ACTION="${1:-}"
POST_ID="${2:-}"
CALLBACK_QUERY_ID="${3:-}"  # optional, for answering Telegram callback

if [ -z "$ACTION" ] || [ -z "$POST_ID" ]; then
  echo "Usage: handle_approval.sh <approve|skip> <post-id> [callback_query_id]" >&2
  exit 1
fi

# Load bot credentials
if [ -f "$HOME/.openclaw/.env" ]; then
  set +u; source "$HOME/.openclaw/.env"; set -u
fi
BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-$(jq -r '.channels.telegram.botToken' "$HOME/.openclaw/openclaw.json" 2>/dev/null || echo "")}"
CHAT_ID="${TELEGRAM_CHAT_ID:-$(jq -r '.channels.telegram.allowFrom[0]' "$HOME/.openclaw/openclaw.json" 2>/dev/null || echo "")}"

# Find the post file
WEEK="${POST_ID%-[0-9]*}"
# POST_ID format: 2026-W13-001 → week is 2026-W13
WEEK="$(echo "$POST_ID" | grep -oE '[0-9]{4}-W[0-9]+' || echo "")"
POST_NUM="$(echo "$POST_ID" | grep -oE '[0-9]+$' || echo "")"

QUEUE_DIR="$QUEUE/$WEEK"
POST_FILE="$(find "$QUEUE_DIR" -name "$(printf '%03d' "$((10#$POST_NUM))")-*.json" 2>/dev/null | head -1 || echo "")"

if [ -z "$POST_FILE" ] || [ ! -f "$POST_FILE" ]; then
  echo "ERROR: post file not found for $POST_ID" >&2
  exit 1
fi

NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Answer the Telegram callback query to clear the loading spinner
if [ -n "$CALLBACK_QUERY_ID" ] && [ -n "$BOT_TOKEN" ]; then
  curl -sS --max-time 10 \
    "https://api.telegram.org/bot${BOT_TOKEN}/answerCallbackQuery" \
    -H "Content-Type: application/json" \
    -d "{\"callback_query_id\":\"${CALLBACK_QUERY_ID}\",\"text\":\"$(echo "$ACTION" | sed 's/approve/✅ Approved/; s/skip/❌ Skipped/')\"}" \
    > /dev/null 2>&1 || true
fi

if [ "$ACTION" = "approve" ]; then
  # Update post status
  TMP="$(mktemp)"
  jq --arg now "$NOW" '.status = "approved" | .approved_at = $now' "$POST_FILE" > "$TMP" \
    || { rm -f "$TMP"; echo "ERROR: jq failed updating post status" >&2; exit 1; }
  mv "$TMP" "$POST_FILE"

  # Update approval.json counts
  TMP="$(mktemp)"
  jq '.pending = [.pending - 1, 0] | max | . as $p | . + {pending:$p, approved:(.approved + 1)}' \
    "$QUEUE_DIR/approval.json" > "$TMP" \
    || { rm -f "$TMP"; echo "ERROR: jq failed updating approval counts" >&2; exit 1; }
  mv "$TMP" "$QUEUE_DIR/approval.json"

  # Check if scheduled time has already passed — post immediately if so
  SCHEDULED="$(jq -r '.scheduled_time' "$POST_FILE")"
  SCHED_EPOCH="$(date -u -d "$SCHEDULED" +%s 2>/dev/null || echo "9999999999")"
  NOW_EPOCH="$(date -u +%s)"

  if [ "$SCHED_EPOCH" -le "$NOW_EPOCH" ]; then
    echo "Scheduled time has passed — posting now..."
    PLATFORM="$(jq -r '.platform' "$POST_FILE")"
    SCRIPT="$POST_SCRIPTS/post_${PLATFORM}.sh"
    PY_SCRIPT="$POST_SCRIPTS/post_${PLATFORM}.py"

    if [ -f "$SCRIPT" ]; then
      "$SCRIPT" "$POST_FILE" || echo "WARNING: posting to $PLATFORM failed" >&2
    elif [ -f "$PY_SCRIPT" ]; then
      python3 "$PY_SCRIPT" "$POST_FILE" || echo "WARNING: posting to $PLATFORM failed" >&2
    else
      echo "NOTE: no post script for $PLATFORM — mark for manual posting" >&2
      TMP="$(mktemp)"
      jq '.status = "manual_required"' "$POST_FILE" > "$TMP" \
        || { rm -f "$TMP"; echo "ERROR: jq failed marking manual_required" >&2; exit 1; }
      mv "$TMP" "$POST_FILE"
    fi
  fi

  # Send confirmation to Telegram
  if [ -n "$BOT_TOKEN" ] && [ -n "$CHAT_ID" ]; then
    PLATFORM="$(jq -r '.platform' "$POST_FILE")"
    curl -sS --max-time 10 \
      "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
      -H "Content-Type: application/json" \
      -d "$(jq -n --argjson chat "$CHAT_ID" --arg text "✅ Approved: $POST_ID ($PLATFORM)" \
        '{chat_id:$chat, text:$text}')" \
      > /dev/null 2>&1 || true
  fi

elif [ "$ACTION" = "skip" ]; then
  TMP="$(mktemp)"
  jq --arg now "$NOW" '.status = "skipped" | .approved_at = $now' "$POST_FILE" > "$TMP" \
    || { rm -f "$TMP"; echo "ERROR: jq failed updating post status" >&2; exit 1; }
  mv "$TMP" "$POST_FILE"

  TMP="$(mktemp)"
  jq '.pending = [.pending - 1, 0] | max | . as $p | . + {pending:$p, skipped:(.skipped + 1)}' \
    "$QUEUE_DIR/approval.json" > "$TMP" \
    || { rm -f "$TMP"; echo "ERROR: jq failed updating approval counts" >&2; exit 1; }
  mv "$TMP" "$QUEUE_DIR/approval.json"

  if [ -n "$BOT_TOKEN" ] && [ -n "$CHAT_ID" ]; then
    PLATFORM="$(jq -r '.platform' "$POST_FILE")"
    curl -sS --max-time 10 \
      "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
      -H "Content-Type: application/json" \
      -d "$(jq -n --argjson chat "$CHAT_ID" --arg text "❌ Skipped: $POST_ID ($PLATFORM)" \
        '{chat_id:$chat, text:$text}')" \
      > /dev/null 2>&1 || true
  fi
else
  echo "ERROR: unknown action '$ACTION' — must be approve or skip" >&2
  exit 1
fi

echo "$ACTION: $POST_ID"
