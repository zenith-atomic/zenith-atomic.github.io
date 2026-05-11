#!/usr/bin/env bash
# Fetch LinkedIn organization post metrics and append to kpi.jsonl
# Requires: LINKEDIN_ACCESS_TOKEN, LINKEDIN_ORG_ID
set -euo pipefail

FACTORY="$HOME/.openclaw/workspace/factory"
ANALYTICS="$FACTORY/analytics"
KPI_FILE="$ANALYTICS/kpi.jsonl"
WEEK="${1:-$(date -u +%Y-W%V)}"

[ -n "${LINKEDIN_ACCESS_TOKEN:-}" ] || { echo "LINKEDIN_ACCESS_TOKEN not set — skipping" >&2; exit 0; }
[ -n "${LINKEDIN_ORG_ID:-}" ] || { echo "LINKEDIN_ORG_ID not set — skipping" >&2; exit 0; }

mkdir -p "$ANALYTICS"

NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# Fetch recent organization shares (posts)
SHARES_RESPONSE="$(curl -sS --max-time 30 \
  "https://api.linkedin.com/v2/shares?q=owners&owners=urn:li:organization:${LINKEDIN_ORG_ID}&count=20&sortBy=LAST_MODIFIED" \
  -H "Authorization: Bearer $LINKEDIN_ACCESS_TOKEN" \
  -H "X-Restli-Protocol-Version: 2.0.0")"

if echo "$SHARES_RESPONSE" | jq -e '.status' > /dev/null 2>&1; then
  echo "LinkedIn API error: $(echo "$SHARES_RESPONSE" | jq -r '.message // .status')" >&2
  exit 1
fi

COUNT=0

while IFS= read -r share; do
  share_id="$(echo "$share" | jq -r '.id' | sed 's|urn:li:share:||')"
  created="$(echo "$share" | jq -r '.created.time // 0' | \
    python3 -c "import sys,datetime; ts=int(sys.stdin.read().strip())//1000; print(datetime.datetime.utcfromtimestamp(ts).strftime('%Y-%m-%dT%H:%M:%SZ'))" 2>/dev/null || echo "$NOW")"

  # Fetch share statistics
  STATS="$(curl -sS --max-time 15 \
    "https://api.linkedin.com/v2/organizationalEntityShareStatistics?q=organizationalEntity&organizationalEntity=urn:li:organization:${LINKEDIN_ORG_ID}&shares=List(urn:li:share:${share_id})" \
    -H "Authorization: Bearer $LINKEDIN_ACCESS_TOKEN" \
    -H "X-Restli-Protocol-Version: 2.0.0" 2>/dev/null || echo '{}')"

  impressions="$(echo "$STATS" | jq -r '.elements[0].totalShareStatistics.impressionCount // 0')"
  clicks="$(echo "$STATS" | jq -r '.elements[0].totalShareStatistics.clickCount // 0')"
  likes="$(echo "$STATS" | jq -r '.elements[0].totalShareStatistics.likeCount // 0')"
  comments="$(echo "$STATS" | jq -r '.elements[0].totalShareStatistics.commentCount // 0')"
  shares="$(echo "$STATS" | jq -r '.elements[0].totalShareStatistics.shareCount // 0')"

  engagements=$((clicks + likes + comments + shares))
  eng_rate=0
  [ "${impressions:-0}" -gt 0 ] && eng_rate="$(echo "scale=4; $engagements / $impressions" | bc 2>/dev/null || echo "0")"

  if [ -f "$KPI_FILE" ] && grep -q "\"post_id\":\"li-${share_id}\"" "$KPI_FILE" 2>/dev/null; then
    TMP="$(mktemp)"
    grep -v "\"post_id\":\"li-${share_id}\"" "$KPI_FILE" > "$TMP" || true
    grep "\"post_id\":\"li-${share_id}\"" "$KPI_FILE" | head -1 | \
      jq --argjson imp "$impressions" --argjson eng "$engagements" \
         --argjson clicks "$clicks" --argjson likes "$likes" \
         --arg now "$NOW" \
         '.impressions=$imp | .engagements=$eng | .clicks=$clicks | .likes=$likes | .last_updated=$now' >> "$TMP"
    mv "$TMP" "$KPI_FILE"
  else
    jq -n \
      --arg id "li-${share_id}" \
      --arg week "$WEEK" \
      --arg logged "$NOW" \
      --arg platform "linkedin" \
      --arg post_id "li-${share_id}" \
      --arg created "$created" \
      --arg source "api" \
      --argjson impressions "${impressions:-0}" \
      --argjson clicks "${clicks:-0}" \
      --argjson likes "${likes:-0}" \
      --argjson comments "${comments:-0}" \
      --argjson shares "${shares:-0}" \
      --argjson engagements "$engagements" \
      --arg eng_rate "$eng_rate" \
      '{id:$id, week:$week, logged:$logged, platform:$platform,
        post_id:$post_id, created_at:$created, source:$source,
        impressions:$impressions, engagements:$engagements,
        clicks:$clicks, likes:$likes, comments:$comments, shares:$shares,
        engagement_rate:($eng_rate|tonumber)}' >> "$KPI_FILE"
    COUNT=$((COUNT + 1))
  fi
done < <(echo "$SHARES_RESPONSE" | jq -c '.elements[]? // empty')

echo "LinkedIn: $COUNT new entries added to kpi.jsonl"
