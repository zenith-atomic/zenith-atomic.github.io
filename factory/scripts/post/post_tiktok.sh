#!/usr/bin/env bash
# TikTok posting — placeholder until Content Posting API access is approved
# TikTok API requires app review (2-4 weeks). Until approved, posts are flagged as manual_required.
# When API access is granted: implement POST /v2/post/publish/video/init flow here.
set -euo pipefail

if [ "${1:-}" = "" ]; then
  echo "Usage: post_tiktok.sh <post-json-file>" >&2
  exit 1
fi

POST_FILE="$1"
if [ ! -f "$POST_FILE" ]; then
  echo "ERROR: post file not found: $POST_FILE" >&2
  exit 1
fi

if [ -f "$HOME/.openclaw/.env" ]; then
  set +u; source "$HOME/.openclaw/.env"; set -u
fi

CONTENT="$(jq -r '.content // ""' "$POST_FILE")"
WEEK="$(jq -r '.week // "unknown"' "$POST_FILE")"
POST_ID="$(jq -r '.id // "unknown"' "$POST_FILE")"
DAY="$(jq -r '.day // ""' "$POST_FILE")"
TIME_ET="$(jq -r '.scheduled_time // ""' "$POST_FILE")"

# If TikTok API tokens are available (post-review), attempt real posting
if [ -n "${TIKTOK_ACCESS_TOKEN:-}" ] && [ -n "${TIKTOK_OPEN_ID:-}" ]; then
  echo "TikTok API tokens found — NOTE: video upload requires a video file path (not text)." >&2
  echo "TikTok does not support text-only posts. Post manually using content below." >&2
  echo ""
  echo "=== TikTok Content for $POST_ID ==="
  echo "$CONTENT"
  echo "==================================="
  exit 1
fi

# No tokens — send Telegram reminder for manual posting
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"

MSG="🎵 *TikTok — Manual Post Required*

*Post ID:* \`${POST_ID}\`
*Week:* ${WEEK} | *Day:* ${DAY}
*Scheduled:* ${TIME_ET}

*Content:*
\`\`\`
$(echo "$CONTENT" | head -c 800)
\`\`\`

TikTok API access is pending review. Please post this manually in the TikTok app."

if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
  curl -sS --max-time 10 \
    "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -H "Content-Type: application/json" \
    -d "$(jq -n \
      --arg chat_id "$TELEGRAM_CHAT_ID" \
      --arg text "$MSG" \
      '{chat_id: $chat_id, text: $text, parse_mode: "Markdown"}')" \
    > /dev/null 2>&1 || true
  echo "TikTok manual reminder sent via Telegram" >&2
fi

# Update post status to manual_required
if [ -f "$POST_FILE" ]; then
  TMP="$(mktemp)"
  jq '.status = "manual_required" | .manual_reason = "TikTok API pending app review"' "$POST_FILE" > "$TMP"
  mv "$TMP" "$POST_FILE"
fi

echo "manual_required:tiktok"
exit 0
