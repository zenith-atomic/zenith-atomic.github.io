#!/usr/bin/env bash
set -euo pipefail

FACTORY="$HOME/.openclaw/workspace/factory"
QUEUE="$FACTORY/queue"

# Load bot credentials
if [ -f "$HOME/.openclaw/.env" ]; then
  # shellcheck disable=SC1091
  set +u; source "$HOME/.openclaw/.env"; set -u
fi

BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-$(jq -r '.channels.telegram.botToken' "$HOME/.openclaw/openclaw.json" 2>/dev/null || echo "")}"
CHAT_ID="${TELEGRAM_CHAT_ID:-$(jq -r '.channels.telegram.allowFrom[0]' "$HOME/.openclaw/openclaw.json" 2>/dev/null || echo "")}"

if [ -z "$BOT_TOKEN" ] || [ -z "$CHAT_ID" ]; then
  echo "ERROR: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set" >&2
  exit 1
fi

WEEK="$(date -u +%Y-W%V)"
QUEUE_DIR="$QUEUE/$WEEK"

if [ ! -d "$QUEUE_DIR" ]; then
  echo "ERROR: queue directory not found: $QUEUE_DIR" >&2
  exit 1
fi

TOTAL="$(jq -r '.total' "$QUEUE_DIR/approval.json" 2>/dev/null || echo "0")"

send_post() {
  local post_file="$1"
  local post_num="$2"

  local post_id platform day scheduled content format pillar
  post_id="$(jq -r '.id' "$post_file")"
  platform="$(jq -r '.platform' "$post_file")"
  day="$(jq -r '.day' "$post_file")"
  scheduled="$(jq -r '.scheduled_time' "$post_file")"
  content="$(jq -r '.content' "$post_file")"
  format="$(jq -r '.format // "post"' "$post_file")"
  pillar="$(jq -r '.pillar // ""' "$post_file")"

  # Format scheduled time for display
  local display_time
  display_time="$(date -u -d "$scheduled" '+%a %b %-d, %-I:%M %p ET' 2>/dev/null || echo "$day")"

  # Truncate content to 300 chars for preview
  local preview
  preview="${content:0:300}"
  [ "${#content}" -gt 300 ] && preview="$preview..."

  local platform_upper
  platform_upper="$(echo "$platform" | tr '[:lower:]' '[:upper:]')"

  local msg
  msg="$(printf 'POST %d/%d — %s — %s\n\n%s\n\nPillar: %s | Format: %s\nScheduled: %s' \
    "$post_num" "$TOTAL" "$platform_upper" "$(echo "$day" | sed 's/./\u&/')" \
    "$preview" "$pillar" "$format" "$display_time")"

  # Send with inline keyboard
  local keyboard
  keyboard="{\"inline_keyboard\":[[{\"text\":\"✅ Approve\",\"callback_data\":\"approve:${post_id}\"},{\"text\":\"❌ Skip\",\"callback_data\":\"skip:${post_id}\"}]]}"

  local response msg_id
  response="$(curl -sS --max-time 15 \
    "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    -H "Content-Type: application/json" \
    -d "$(jq -n \
      --argjson chat "$CHAT_ID" \
      --arg text "$msg" \
      --argjson reply_markup "$keyboard" \
      '{chat_id:$chat, text:$text, reply_markup:$reply_markup, parse_mode:"HTML"}')" 2>/dev/null)"

  msg_id="$(echo "$response" | jq -r '.result.message_id // empty')"
  if [ -n "$msg_id" ]; then
    # Store message_id in the post file
    local TMP
    TMP="$(mktemp)"
    jq --argjson mid "$msg_id" '.telegram_message_id = $mid' "$post_file" > "$TMP"
    mv "$TMP" "$post_file"
  else
    echo "WARNING: failed to send post $post_id to Telegram" >&2
  fi

  # Small delay to avoid Telegram rate limits
  sleep 0.5
}

POST_NUM=0
while IFS= read -r -d '' post_file; do
  [[ "$post_file" == *"approval.json" ]] && continue
  POST_NUM=$((POST_NUM + 1))
  STATUS="$(jq -r '.status' "$post_file")"
  if [ "$STATUS" = "pending" ]; then
    send_post "$post_file" "$POST_NUM"
  fi
done < <(find "$QUEUE_DIR" -name '*.json' ! -name 'approval.json' | sort -z)

echo "Sent $POST_NUM posts to Telegram for approval"
