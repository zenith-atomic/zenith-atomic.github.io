#!/usr/bin/env bash
# Fetch Twitter/X post metrics and append to kpi.jsonl
# Requires: TWITTER_BEARER_TOKEN, TWITTER_USER_ID
set -euo pipefail

FACTORY="$HOME/.openclaw/workspace/factory"
ANALYTICS="$FACTORY/analytics"
KPI_FILE="$ANALYTICS/kpi.jsonl"
WEEK="${1:-$(date -u +%Y-W%V)}"

[ -n "${TWITTER_BEARER_TOKEN:-}" ] || { echo "TWITTER_BEARER_TOKEN not set — skipping" >&2; exit 0; }
[ -n "${TWITTER_USER_ID:-}" ] || { echo "TWITTER_USER_ID not set — skipping" >&2; exit 0; }

mkdir -p "$ANALYTICS"

# Fetch recent tweets with public metrics (last 7 days)
START_TIME="$(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || \
              python3 -c "import datetime; print((datetime.datetime.utcnow()-datetime.timedelta(7)).strftime('%Y-%m-%dT%H:%M:%SZ'))")"

RESPONSE="$(curl -sS --max-time 30 \
  "https://api.twitter.com/2/users/${TWITTER_USER_ID}/tweets?max_results=100&tweet.fields=public_metrics,created_at&start_time=${START_TIME}" \
  -H "Authorization: Bearer $TWITTER_BEARER_TOKEN")"

# Check for errors
if echo "$RESPONSE" | jq -e '.errors' > /dev/null 2>&1; then
  echo "Twitter API error: $(echo "$RESPONSE" | jq -r '.errors[0].message // .errors')" >&2
  exit 1
fi

NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
COUNT=0

while IFS= read -r tweet; do
  tweet_id="$(echo "$tweet" | jq -r '.id')"
  created="$(echo "$tweet" | jq -r '.created_at')"
  metrics="$(echo "$tweet" | jq -r '.public_metrics')"

  impressions="$(echo "$metrics" | jq -r '.impression_count // 0')"
  likes="$(echo "$metrics" | jq -r '.like_count // 0')"
  retweets="$(echo "$metrics" | jq -r '.retweet_count // 0')"
  replies="$(echo "$metrics" | jq -r '.reply_count // 0')"
  quotes="$(echo "$metrics" | jq -r '.quote_count // 0')"
  clicks="$(echo "$metrics" | jq -r '.url_link_clicks // 0')"

  engagements=$((likes + retweets + replies + quotes + clicks))
  eng_rate=0
  [ "$impressions" -gt 0 ] && eng_rate="$(echo "scale=4; $engagements / $impressions" | bc 2>/dev/null || echo "0")"

  # Avoid duplicates — skip if already logged
  if [ -f "$KPI_FILE" ] && grep -q "\"post_id\":\"tw-${tweet_id}\"" "$KPI_FILE" 2>/dev/null; then
    # Update existing entry instead
    UPDATED="$(grep "\"post_id\":\"tw-${tweet_id}\"" "$KPI_FILE" | head -1 | \
      jq --argjson imp "$impressions" --argjson eng "$engagements" \
         --argjson likes "$likes" --argjson rt "$retweets" \
         --arg now "$NOW" \
         '.impressions=$imp | .engagements=$eng | .likes=$likes | .retweets=$rt | .last_updated=$now')"
    TMP="$(mktemp)"
    grep -v "\"post_id\":\"tw-${tweet_id}\"" "$KPI_FILE" > "$TMP" || true
    echo "$UPDATED" >> "$TMP"
    mv "$TMP" "$KPI_FILE"
  else
    jq -n \
      --arg id "tw-${tweet_id}" \
      --arg week "$WEEK" \
      --arg logged "$NOW" \
      --arg platform "twitter" \
      --arg post_id "tw-${tweet_id}" \
      --arg created "$created" \
      --arg source "api" \
      --argjson impressions "$impressions" \
      --argjson engagements "$engagements" \
      --argjson likes "$likes" \
      --argjson retweets "$retweets" \
      --argjson replies "$replies" \
      --argjson clicks "$clicks" \
      --arg eng_rate "$eng_rate" \
      '{id:$id, week:$week, logged:$logged, platform:$platform,
        post_id:$post_id, created_at:$created, source:$source,
        impressions:$impressions, engagements:$engagements,
        likes:$likes, retweets:$retweets, replies:$replies, clicks:$clicks,
        engagement_rate:($eng_rate|tonumber)}' >> "$KPI_FILE"
    COUNT=$((COUNT + 1))
  fi
done < <(echo "$RESPONSE" | jq -c '.data[]? // empty')

echo "Twitter: $COUNT new entries added to kpi.jsonl"
