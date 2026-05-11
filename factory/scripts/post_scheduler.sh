#!/usr/bin/env bash
set -euo pipefail

FACTORY="$HOME/.openclaw/workspace/factory"
QUEUE="$FACTORY/queue"
POST_SCRIPTS="$FACTORY/scripts/post"
ANALYTICS="$FACTORY/analytics"

if [ -f "$HOME/.openclaw/.env" ]; then
  set +u; source "$HOME/.openclaw/.env"; set -u
fi
BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-$(jq -r '.channels.telegram.botToken' "$HOME/.openclaw/openclaw.json" 2>/dev/null || echo "")}"
CHAT_ID="${TELEGRAM_CHAT_ID:-$(jq -r '.channels.telegram.allowFrom[0]' "$HOME/.openclaw/openclaw.json" 2>/dev/null || echo "")}"

NOW_EPOCH="$(date -u +%s)"
NOW_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

send_alert() {
  local msg="$1"
  [ -n "$BOT_TOKEN" ] && [ -n "$CHAT_ID" ] || return 0
  curl -sS --max-time 10 \
    "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    -H "Content-Type: application/json" \
    -d "$(jq -n --argjson chat "$CHAT_ID" --arg text "$msg" '{chat_id:$chat, text:$text}')" \
    > /dev/null 2>&1 || true
}

post_content() {
  local post_file="$1"
  local platform="$2"
  local script="$POST_SCRIPTS/post_${platform}.sh"
  local py_script="$POST_SCRIPTS/post_${platform}.py"
  local retry_count

  retry_count="$(jq -r '.retry_count // 0' "$post_file")"

  if [ -f "$script" ]; then
    POST_URL="$("$script" "$post_file" 2>/dev/null)"
  elif [ -f "$py_script" ]; then
    POST_URL="$(python3 "$py_script" "$post_file" 2>/dev/null)"
  else
    # No posting script — mark as manual_required
    TMP="$(mktemp)"
    jq --arg now "$NOW_ISO" '.status = "manual_required" | .posted_at = $now' "$post_file" > "$TMP"
    mv "$TMP" "$post_file"
    send_alert "⚠️ Manual post required: $(jq -r '.id' "$post_file") on $platform"
    return 0
  fi

  if [ $? -eq 0 ] && [ -n "${POST_URL:-}" ]; then
    # Success
    TMP="$(mktemp)"
    jq --arg now "$NOW_ISO" --arg url "$POST_URL" \
      '.status = "posted" | .posted_at = $now | .post_url = $url' "$post_file" > "$TMP"
    mv "$TMP" "$post_file"

    # Append to published.log
    WEEK="$(jq -r '.week' "$post_file")"
    PUBLISHED_LOG="$FACTORY/output/$WEEK/published.log"
    printf '%s | %s | %s | %s | posted\n' \
      "$NOW_ISO" "$platform" "$(jq -r '.id' "$post_file")" "$POST_URL" >> "$PUBLISHED_LOG"

    send_alert "✅ Posted: $(jq -r '.id' "$post_file") on $platform\n$POST_URL"
  else
    # Failure — increment retry count
    retry_count=$((retry_count + 1))
    TMP="$(mktemp)"
    jq --argjson rc "$retry_count" '.retry_count = $rc' "$post_file" > "$TMP"
    mv "$TMP" "$post_file"

    if [ "$retry_count" -ge 3 ]; then
      TMP="$(mktemp)"
      jq '.status = "failed"' "$post_file" > "$TMP"
      mv "$TMP" "$post_file"
      send_alert "❌ Post failed after 3 attempts: $(jq -r '.id' "$post_file") on $platform — manual action required"
    fi
  fi
}

# Scan all queue week directories
while IFS= read -r -d '' post_file; do
  [[ "$post_file" == *"approval.json" ]] && continue

  STATUS="$(jq -r '.status' "$post_file")"
  [ "$STATUS" != "approved" ] && continue

  SCHEDULED="$(jq -r '.scheduled_time' "$post_file")"
  SCHED_EPOCH="$(date -u -d "$SCHEDULED" +%s 2>/dev/null || echo "9999999999")"

  if [ "$SCHED_EPOCH" -le "$NOW_EPOCH" ]; then
    PLATFORM="$(jq -r '.platform' "$post_file")"
    echo "Posting: $(jq -r '.id' "$post_file") to $PLATFORM"
    post_content "$post_file" "$PLATFORM"
  fi
done < <(find "$QUEUE" -name '*.json' ! -name 'approval.json' -print0 2>/dev/null)
