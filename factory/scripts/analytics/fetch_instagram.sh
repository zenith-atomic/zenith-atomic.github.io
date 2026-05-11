#!/usr/bin/env bash
# Fetch Instagram post metrics via Graph API and append to kpi.jsonl
# Requires: INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_USER_ID, META_APP_ID, META_APP_SECRET
set -euo pipefail

FACTORY="$HOME/.openclaw/workspace/factory"
ANALYTICS="$FACTORY/analytics"
KPI_FILE="$ANALYTICS/kpi.jsonl"
WEEK="${1:-$(date -u +%Y-W%V)}"

[ -n "${INSTAGRAM_ACCESS_TOKEN:-}" ] || { echo "INSTAGRAM_ACCESS_TOKEN not set — skipping" >&2; exit 0; }
[ -n "${INSTAGRAM_USER_ID:-}" ] || { echo "INSTAGRAM_USER_ID not set — skipping" >&2; exit 0; }

mkdir -p "$ANALYTICS"

# Auto-refresh token if within 7 days of expiry (token expiry is stored in .env as INSTAGRAM_TOKEN_EXPIRY unix epoch)
if [ -n "${META_APP_ID:-}" ] && [ -n "${META_APP_SECRET:-}" ]; then
  EXPIRY="${INSTAGRAM_TOKEN_EXPIRY:-0}"
  NOW_EPOCH="$(date -u +%s)"
  DAYS_LEFT=$(( (EXPIRY - NOW_EPOCH) / 86400 ))
  if [ "$DAYS_LEFT" -lt 7 ] && [ "$EXPIRY" -gt 0 ]; then
    echo "Instagram token expiring in $DAYS_LEFT days — refreshing..." >&2
    NEW_TOKEN_RESP="$(curl -sS --max-time 15 \
      "https://graph.facebook.com/v19.0/oauth/access_token?grant_type=fb_exchange_token&client_id=${META_APP_ID}&client_secret=${META_APP_SECRET}&fb_exchange_token=${INSTAGRAM_ACCESS_TOKEN}")"
    NEW_TOKEN="$(echo "$NEW_TOKEN_RESP" | jq -r '.access_token // empty')"
    if [ -n "$NEW_TOKEN" ]; then
      NEW_EXPIRY=$((NOW_EPOCH + 5184000))  # 60 days
      sed -i "s|INSTAGRAM_ACCESS_TOKEN=.*|INSTAGRAM_ACCESS_TOKEN=$NEW_TOKEN|" "$HOME/.openclaw/.env" || true
      sed -i "s|INSTAGRAM_TOKEN_EXPIRY=.*|INSTAGRAM_TOKEN_EXPIRY=$NEW_EXPIRY|" "$HOME/.openclaw/.env" || true
      INSTAGRAM_ACCESS_TOKEN="$NEW_TOKEN"
      echo "Instagram token refreshed successfully" >&2
    else
      echo "WARNING: Instagram token refresh failed — $(echo "$NEW_TOKEN_RESP" | jq -r '.error.message // .')" >&2
    fi
  fi
fi

# Fetch recent media (last 25 posts)
MEDIA_RESPONSE="$(curl -sS --max-time 30 \
  "https://graph.facebook.com/v19.0/${INSTAGRAM_USER_ID}/media?fields=id,caption,media_type,timestamp,like_count,comments_count&limit=25&access_token=${INSTAGRAM_ACCESS_TOKEN}")"

if echo "$MEDIA_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
  echo "Instagram API error: $(echo "$MEDIA_RESPONSE" | jq -r '.error.message')" >&2
  exit 1
fi

NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
COUNT=0

while IFS= read -r media; do
  media_id="$(echo "$media" | jq -r '.id')"
  created="$(echo "$media" | jq -r '.timestamp')"
  likes="$(echo "$media" | jq -r '.like_count // 0')"
  comments="$(echo "$media" | jq -r '.comments_count // 0')"

  # Fetch insights per media (impressions, reach, saved)
  INSIGHTS="$(curl -sS --max-time 15 \
    "https://graph.facebook.com/v19.0/${media_id}/insights?metric=impressions,reach,saved&access_token=${INSTAGRAM_ACCESS_TOKEN}" 2>/dev/null || echo '{}')"

  impressions="$(echo "$INSIGHTS" | jq -r '[.data[]? | select(.name=="impressions") | .values[0].value] | first // 0')"
  reach="$(echo "$INSIGHTS" | jq -r '[.data[]? | select(.name=="reach") | .values[0].value] | first // 0')"
  saved="$(echo "$INSIGHTS" | jq -r '[.data[]? | select(.name=="saved") | .values[0].value] | first // 0')"

  [ -z "$impressions" ] || [ "$impressions" = "null" ] && impressions=0
  engagements=$((likes + comments + saved))
  eng_rate=0
  [ "$impressions" -gt 0 ] && eng_rate="$(echo "scale=4; $engagements / $impressions" | bc 2>/dev/null || echo "0")"

  if [ -f "$KPI_FILE" ] && grep -q "\"post_id\":\"ig-${media_id}\"" "$KPI_FILE" 2>/dev/null; then
    TMP="$(mktemp)"
    grep -v "\"post_id\":\"ig-${media_id}\"" "$KPI_FILE" > "$TMP" || true
    grep "\"post_id\":\"ig-${media_id}\"" "$KPI_FILE" | head -1 | \
      jq --argjson imp "$impressions" --argjson eng "$engagements" \
         --argjson likes "$likes" --argjson comments "$comments" \
         --arg now "$NOW" \
         '.impressions=$imp | .engagements=$eng | .likes=$likes | .comments=$comments | .last_updated=$now' >> "$TMP"
    mv "$TMP" "$KPI_FILE"
  else
    jq -n \
      --arg id "ig-${media_id}" \
      --arg week "$WEEK" \
      --arg logged "$NOW" \
      --arg platform "instagram" \
      --arg post_id "ig-${media_id}" \
      --arg created "$created" \
      --arg source "api" \
      --argjson impressions "$impressions" \
      --argjson reach "$reach" \
      --argjson engagements "$engagements" \
      --argjson likes "$likes" \
      --argjson comments "$comments" \
      --argjson saved "$saved" \
      --arg eng_rate "$eng_rate" \
      '{id:$id, week:$week, logged:$logged, platform:$platform,
        post_id:$post_id, created_at:$created, source:$source,
        impressions:$impressions, reach:$reach, engagements:$engagements,
        likes:$likes, comments:$comments, saved:$saved,
        engagement_rate:($eng_rate|tonumber)}' >> "$KPI_FILE"
    COUNT=$((COUNT + 1))
  fi
done < <(echo "$MEDIA_RESPONSE" | jq -c '.data[]? // empty')

echo "Instagram: $COUNT new entries added to kpi.jsonl"
