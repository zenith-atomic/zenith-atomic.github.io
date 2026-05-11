#!/usr/bin/env bash
set -euo pipefail

FACTORY="$HOME/.openclaw/workspace/factory"
SCRIPTS="$FACTORY/scripts"
AGENTS="$FACTORY/agents"
QUEUE="$FACTORY/queue"

WEEK="$(date -u +%Y-W%V)"
WEEK_DIR="$FACTORY/output/$WEEK"
QUEUE_DIR="$QUEUE/$WEEK"

if [ ! -f "$WEEK_DIR/publishing_checklist.md" ]; then
  echo "ERROR: publishing_checklist.md not found. Run /factory publish first." >&2
  exit 1
fi

mkdir -p "$QUEUE_DIR"

CHECKLIST="$(cat "$WEEK_DIR/publishing_checklist.md")"

echo "Parsing publishing checklist into queue..."
POSTS_JSON="$("$SCRIPTS/call_agent.sh" "$AGENTS/stage_posts.prompt" "$CHECKLIST" "gpt-5.4-mini" "4000")"

# Validate it's a JSON array
if ! echo "$POSTS_JSON" | jq -e '. | type == "array"' > /dev/null 2>&1; then
  echo "ERROR: stage_posts LLM did not return a JSON array" >&2
  echo "Response: $POSTS_JSON" >&2
  exit 1
fi

TOTAL="$(echo "$POSTS_JSON" | jq 'length')"
echo "Parsed $TOTAL posts from checklist"

# Day-to-date mapping for current week (Monday = start of ISO week)
WEEK_NUM="${WEEK#*-W}"
YEAR="${WEEK%-W*}"
# Get the Monday of this week
MONDAY="$(date -u -d "${YEAR}-01-01 +$((WEEK_NUM - 1)) weeks" +%Y-%m-%d 2>/dev/null || \
          python3 -c "import datetime; y,w=int('$YEAR'),int('$WEEK_NUM'); d=datetime.datetime.strptime(f'{y} {w} 1','%Y %W %w'); print(d.strftime('%Y-%m-%d'))")"

declare -A DAY_OFFSET=(
  [monday]=0 [tuesday]=1 [wednesday]=2 [thursday]=3
  [friday]=4 [saturday]=5 [sunday]=6
)

# Write one JSON file per post
POST_NUM=0
for row in $(echo "$POSTS_JSON" | jq -r '.[] | @base64'); do
  POST_NUM=$((POST_NUM + 1))
  DATA="$(echo "$row" | base64 -d)"

  PLATFORM="$(echo "$DATA" | jq -r '.platform // "unknown"')"
  DAY="$(echo "$DATA" | jq -r '.day // "monday"' | tr '[:upper:]' '[:lower:]')"
  TIME_ET="$(echo "$DATA" | jq -r '.time_et // "09:00"')"

  # Compute UTC scheduled time
  OFFSET="${DAY_OFFSET[$DAY]:-0}"
  POST_DATE="$(date -u -d "$MONDAY + $OFFSET days" +%Y-%m-%d 2>/dev/null || \
               python3 -c "import datetime; d=datetime.date.fromisoformat('$MONDAY')+datetime.timedelta($OFFSET); print(d)")"
  # ET is UTC-4 (EDT) or UTC-5 (EST) — use UTC-4 as approximation for spring
  HOUR="$(echo "$TIME_ET" | cut -d: -f1)"
  MIN="$(echo "$TIME_ET" | cut -d: -f2)"
  UTC_HOUR=$(( (10#$HOUR + 4) % 24 ))
  SCHEDULED="${POST_DATE}T$(printf '%02d' "$UTC_HOUR"):${MIN}:00Z"

  POST_ID="$(printf '%s-%03d' "$WEEK" "$POST_NUM")"
  POST_FILE="$QUEUE_DIR/$(printf '%03d' "$POST_NUM")-${PLATFORM}.json"

  echo "$DATA" | jq \
    --arg id "$POST_ID" \
    --arg week "$WEEK" \
    --arg scheduled "$SCHEDULED" \
    '. + {id:$id, week:$week, scheduled_time:$scheduled,
           status:"pending", telegram_message_id:null,
           approved_at:null, posted_at:null, post_url:null}' \
    > "$POST_FILE"
done

# Write approval.json summary
jq -n \
  --arg week "$WEEK" \
  --argjson total "$TOTAL" \
  '{week:$week, total:$total, pending:$total, approved:0, skipped:0, posted:0}' \
  > "$QUEUE_DIR/approval.json"

echo "Queue created: $QUEUE_DIR ($TOTAL posts)"

# Kick off Telegram approval flow
if [ -f "$SCRIPTS/telegram_approval_bot.sh" ]; then
  echo "Sending posts to Telegram for approval..."
  "$SCRIPTS/telegram_approval_bot.sh" &
fi
