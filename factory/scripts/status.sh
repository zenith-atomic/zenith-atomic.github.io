#!/usr/bin/env bash
set -euo pipefail

FACTORY="$HOME/.openclaw/workspace/factory"

# Resolve current week
WEEK="$(date -u +%Y-W%V)"
WEEK_DIR="$FACTORY/output/$WEEK"
STATE_FILE="$WEEK_DIR/pipeline.state"

echo "Content Factory — Week $WEEK"
echo "=============================="

if [ ! -f "$STATE_FILE" ]; then
  echo "No pipeline started for this week."
  echo "Run: /factory run or /factory research"
  exit 0
fi

# Read pipeline state
echo ""
echo "Pipeline Status:"
for STAGE in research strategy writing visuals publishing analytics evolution; do
  STATUS="$(jq -r ".stages.${STAGE}.status" "$STATE_FILE")"
  COMPLETED="$(jq -r ".stages.${STAGE}.completed // empty" "$STATE_FILE")"

  if [ "$STATUS" = "done" ]; then
    ICON="[done]"
    EXTRA=" ($COMPLETED)"
  else
    ICON="[    ]"
    EXTRA=""
  fi
  printf "  %s %-12s%s\n" "$ICON" "$STAGE" "$EXTRA"
done

# Count drafts if they exist
echo ""
if [ -d "$WEEK_DIR/drafts" ]; then
  DRAFT_COUNT="$(find "$WEEK_DIR/drafts" -name '*.md' -not -name 'all_drafts.md' | wc -l)"
  echo "Drafts: $DRAFT_COUNT"
else
  echo "Drafts: 0"
fi

# Count KPI entries for this week
if [ -f "$FACTORY/analytics/kpi.jsonl" ]; then
  KPI_COUNT="$(grep -c "\"$WEEK\"" "$FACTORY/analytics/kpi.jsonl" 2>/dev/null || echo 0)"
  echo "KPIs logged: $KPI_COUNT"
fi

# Show published count
if [ -f "$WEEK_DIR/published.log" ]; then
  PUB_COUNT="$(grep -cv '^#' "$WEEK_DIR/published.log" 2>/dev/null || echo 0)"
  echo "Published: $PUB_COUNT"
fi
