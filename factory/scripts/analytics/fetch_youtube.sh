#!/usr/bin/env bash
# Fetch YouTube channel metrics via Analytics API and append to kpi.jsonl
# Requires: YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN, YOUTUBE_CHANNEL_ID
set -euo pipefail

FACTORY="$HOME/.openclaw/workspace/factory"
ANALYTICS="$FACTORY/analytics"
KPI_FILE="$ANALYTICS/kpi.jsonl"
WEEK="${1:-$(date -u +%Y-W%V)}"

[ -n "${YOUTUBE_REFRESH_TOKEN:-}" ] || { echo "YOUTUBE_REFRESH_TOKEN not set — skipping" >&2; exit 0; }
[ -n "${YOUTUBE_CHANNEL_ID:-}" ] || { echo "YOUTUBE_CHANNEL_ID not set — skipping" >&2; exit 0; }

mkdir -p "$ANALYTICS"

# Refresh access token
TOKEN_RESP="$(curl -sS --max-time 15 \
  "https://oauth2.googleapis.com/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=${YOUTUBE_CLIENT_ID}&client_secret=${YOUTUBE_CLIENT_SECRET}&refresh_token=${YOUTUBE_REFRESH_TOKEN}&grant_type=refresh_token")"

ACCESS_TOKEN="$(echo "$TOKEN_RESP" | jq -r '.access_token // empty')"
if [ -z "$ACCESS_TOKEN" ]; then
  echo "YouTube token refresh failed: $(echo "$TOKEN_RESP" | jq -r '.error_description // .error // .')" >&2
  exit 1
fi

NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
START_DATE="$(date -u -d '7 days ago' +%Y-%m-%d 2>/dev/null || \
              python3 -c "import datetime; print((datetime.date.today()-datetime.timedelta(7)).isoformat())")"
END_DATE="$(date -u +%Y-%m-%d)"

# Fetch per-video analytics
ANALYTICS_RESP="$(curl -sS --max-time 30 \
  "https://youtubeanalytics.googleapis.com/v2/reports?ids=channel==MINE&startDate=${START_DATE}&endDate=${END_DATE}&metrics=views,likes,comments,shares,estimatedMinutesWatched,averageViewDuration&dimensions=video&maxResults=50&sort=-views" \
  -H "Authorization: Bearer $ACCESS_TOKEN")"

if echo "$ANALYTICS_RESP" | jq -e '.error' > /dev/null 2>&1; then
  echo "YouTube Analytics API error: $(echo "$ANALYTICS_RESP" | jq -r '.error.message')" >&2
  exit 1
fi

# Column headers: video, views, likes, comments, shares, estimatedMinutesWatched, averageViewDuration
COLUMN_HEADERS="$(echo "$ANALYTICS_RESP" | jq -r '[.columnHeaders[].name] | @json')"

COUNT=0
while IFS= read -r row; do
  video_id="$(echo "$row" | jq -r '.[0]')"
  views="$(echo "$row" | jq -r '.[1] // 0')"
  likes="$(echo "$row" | jq -r '.[2] // 0')"
  comments="$(echo "$row" | jq -r '.[3] // 0')"
  shares="$(echo "$row" | jq -r '.[4] // 0')"
  watch_mins="$(echo "$row" | jq -r '.[5] // 0')"
  avg_duration="$(echo "$row" | jq -r '.[6] // 0')"

  engagements=$((likes + comments + shares))
  eng_rate=0
  [ "${views:-0}" -gt 0 ] && eng_rate="$(echo "scale=4; $engagements / $views" | bc 2>/dev/null || echo "0")"

  if [ -f "$KPI_FILE" ] && grep -q "\"post_id\":\"yt-${video_id}\"" "$KPI_FILE" 2>/dev/null; then
    TMP="$(mktemp)"
    grep -v "\"post_id\":\"yt-${video_id}\"" "$KPI_FILE" > "$TMP" || true
    grep "\"post_id\":\"yt-${video_id}\"" "$KPI_FILE" | head -1 | \
      jq --argjson views "$views" --argjson eng "$engagements" \
         --argjson likes "$likes" --arg now "$NOW" \
         '.impressions=$views | .engagements=$eng | .likes=$likes | .last_updated=$now' >> "$TMP"
    mv "$TMP" "$KPI_FILE"
  else
    jq -n \
      --arg id "yt-${video_id}" \
      --arg week "$WEEK" \
      --arg logged "$NOW" \
      --arg platform "youtube" \
      --arg post_id "yt-${video_id}" \
      --arg source "api" \
      --argjson views "$views" \
      --argjson likes "$likes" \
      --argjson comments "$comments" \
      --argjson shares "$shares" \
      --argjson watch_mins "$watch_mins" \
      --argjson avg_duration "$avg_duration" \
      --argjson engagements "$engagements" \
      --arg eng_rate "$eng_rate" \
      '{id:$id, week:$week, logged:$logged, platform:$platform,
        post_id:$post_id, source:$source,
        impressions:$views, views:$views, engagements:$engagements,
        likes:$likes, comments:$comments, shares:$shares,
        watch_minutes:$watch_mins, avg_view_duration:$avg_duration,
        engagement_rate:($eng_rate|tonumber)}' >> "$KPI_FILE"
    COUNT=$((COUNT + 1))
  fi
done < <(echo "$ANALYTICS_RESP" | jq -c '.rows[]? // empty')

echo "YouTube: $COUNT new entries added to kpi.jsonl"
