#!/usr/bin/env bash
# Fetch TikTok video metrics via Display API and append to kpi.jsonl
# Requires: TIKTOK_ACCESS_TOKEN, TIKTOK_OPEN_ID
# NOTE: TikTok API requires app review approval — exits silently if tokens not set
set -euo pipefail

FACTORY="$HOME/.openclaw/workspace/factory"
ANALYTICS="$FACTORY/analytics"
KPI_FILE="$ANALYTICS/kpi.jsonl"
WEEK="${1:-$(date -u +%Y-W%V)}"

[ -n "${TIKTOK_ACCESS_TOKEN:-}" ] || { echo "TIKTOK_ACCESS_TOKEN not set — skipping (app review required)" >&2; exit 0; }
[ -n "${TIKTOK_OPEN_ID:-}" ] || { echo "TIKTOK_OPEN_ID not set — skipping" >&2; exit 0; }

mkdir -p "$ANALYTICS"

NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Refresh access token if refresh token available
if [ -n "${TIKTOK_CLIENT_KEY:-}" ] && [ -n "${TIKTOK_REFRESH_TOKEN:-}" ]; then
  REFRESH_RESP="$(curl -sS --max-time 15 \
    "https://open.tiktokapis.com/v2/oauth/token/" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "client_key=${TIKTOK_CLIENT_KEY}&client_secret=${TIKTOK_CLIENT_SECRET:-}&grant_type=refresh_token&refresh_token=${TIKTOK_REFRESH_TOKEN}" 2>/dev/null || echo '{}')"
  NEW_TOKEN="$(echo "$REFRESH_RESP" | jq -r '.data.access_token // empty')"
  if [ -n "$NEW_TOKEN" ]; then
    TIKTOK_ACCESS_TOKEN="$NEW_TOKEN"
    sed -i "s|TIKTOK_ACCESS_TOKEN=.*|TIKTOK_ACCESS_TOKEN=$NEW_TOKEN|" "$HOME/.openclaw/.env" || true
  fi
fi

# Fetch video list
VIDEO_RESP="$(curl -sS --max-time 30 \
  "https://open.tiktokapis.com/v2/video/list/?fields=id,create_time,statistics" \
  -H "Authorization: Bearer $TIKTOK_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"max_count":20}' 2>/dev/null || echo '{}')"

if echo "$VIDEO_RESP" | jq -e '.error.code' > /dev/null 2>&1; then
  ERR="$(echo "$VIDEO_RESP" | jq -r '.error.message // .error.code')"
  echo "TikTok API error: $ERR" >&2
  exit 1
fi

COUNT=0
while IFS= read -r video; do
  video_id="$(echo "$video" | jq -r '.id')"
  created_ts="$(echo "$video" | jq -r '.create_time // 0')"
  created="$(date -u -d "@$created_ts" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo "$NOW")"

  views="$(echo "$video" | jq -r '.statistics.play_count // 0')"
  likes="$(echo "$video" | jq -r '.statistics.digg_count // 0')"
  comments="$(echo "$video" | jq -r '.statistics.comment_count // 0')"
  shares="$(echo "$video" | jq -r '.statistics.share_count // 0')"

  engagements=$((likes + comments + shares))
  eng_rate=0
  [ "${views:-0}" -gt 0 ] && eng_rate="$(echo "scale=4; $engagements / $views" | bc 2>/dev/null || echo "0")"

  if [ -f "$KPI_FILE" ] && grep -q "\"post_id\":\"tt-${video_id}\"" "$KPI_FILE" 2>/dev/null; then
    TMP="$(mktemp)"
    grep -v "\"post_id\":\"tt-${video_id}\"" "$KPI_FILE" > "$TMP" || true
    grep "\"post_id\":\"tt-${video_id}\"" "$KPI_FILE" | head -1 | \
      jq --argjson views "$views" --argjson eng "$engagements" \
         --argjson likes "$likes" --arg now "$NOW" \
         '.impressions=$views | .views=$views | .engagements=$eng | .likes=$likes | .last_updated=$now' >> "$TMP"
    mv "$TMP" "$KPI_FILE"
  else
    jq -n \
      --arg id "tt-${video_id}" \
      --arg week "$WEEK" \
      --arg logged "$NOW" \
      --arg platform "tiktok" \
      --arg post_id "tt-${video_id}" \
      --arg created "$created" \
      --arg source "api" \
      --argjson views "$views" \
      --argjson likes "$likes" \
      --argjson comments "$comments" \
      --argjson shares "$shares" \
      --argjson engagements "$engagements" \
      --arg eng_rate "$eng_rate" \
      '{id:$id, week:$week, logged:$logged, platform:$platform,
        post_id:$post_id, created_at:$created, source:$source,
        impressions:$views, views:$views, engagements:$engagements,
        likes:$likes, comments:$comments, shares:$shares,
        engagement_rate:($eng_rate|tonumber)}' >> "$KPI_FILE"
    COUNT=$((COUNT + 1))
  fi
done < <(echo "$VIDEO_RESP" | jq -c '.data.videos[]? // empty')

echo "TikTok: $COUNT new entries added to kpi.jsonl"
