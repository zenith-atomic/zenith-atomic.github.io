#!/usr/bin/env bash
set -euo pipefail

FACTORY="$HOME/.openclaw/workspace/factory"
SCRIPTS="$FACTORY/scripts"
ANALYTICS="$FACTORY/analytics"
KPI_FILE="$ANALYTICS/kpi.jsonl"

WEEK="${1:-$(date -u +%Y-W%V)}"

if [ -f "$HOME/.openclaw/.env" ]; then
  set +u; source "$HOME/.openclaw/.env"; set -u
fi

mkdir -p "$ANALYTICS"
echo "Fetching analytics for $WEEK..."

PLATFORMS=(twitter instagram linkedin youtube tiktok)
for PLATFORM in "${PLATFORMS[@]}"; do
  SCRIPT="$SCRIPTS/analytics/fetch_${PLATFORM}.sh"
  if [ -f "$SCRIPT" ]; then
    echo "  → $PLATFORM"
    bash "$SCRIPT" "$WEEK" || echo "  WARNING: $PLATFORM fetch failed (continuing)" >&2
  fi
done

# Generate/update weekly_summary.jsonl entry
if [ -f "$KPI_FILE" ]; then
  WEEK_DATA="$(grep "\"week\":\"$WEEK\"" "$KPI_FILE" 2>/dev/null || true)"
  if [ -n "$WEEK_DATA" ]; then
    SUMMARY="$(echo "$WEEK_DATA" | jq -s \
      --arg week "$WEEK" \
      --arg generated "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
      '{
        week: $week,
        generated: $generated,
        total_posts: length,
        total_impressions: (map(.impressions // 0) | add // 0),
        total_engagements: (map(.engagements // 0) | add // 0),
        avg_engagement_rate: (map(.engagement_rate // 0) | add / (length | if . == 0 then 1 else . end) * 10000 | round / 10000),
        by_platform: (group_by(.platform) | map({
          platform: .[0].platform,
          posts: length,
          impressions: (map(.impressions // 0) | add // 0),
          engagements: (map(.engagements // 0) | add // 0)
        }))
      }')"

    SUMMARY_FILE="$ANALYTICS/weekly_summary.jsonl"
    TMP="$(mktemp)"
    [ -f "$SUMMARY_FILE" ] && grep -v "\"week\":\"$WEEK\"" "$SUMMARY_FILE" > "$TMP" || true
    echo "$SUMMARY" >> "$TMP"
    mv "$TMP" "$SUMMARY_FILE"
    echo "Weekly summary updated: $SUMMARY_FILE"
  fi
fi

echo "Analytics fetch complete for $WEEK"
