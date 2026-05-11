#!/usr/bin/env bash
set -euo pipefail

FACTORY="$HOME/.openclaw/workspace/factory"
SCRIPTS="$FACTORY/scripts"
AGENTS="$FACTORY/agents"
CONFIG="${FACTORY_CONFIG:-$FACTORY/config}"
ANALYTICS="${FACTORY_ANALYTICS:-$FACTORY/analytics}"

# Resolve current week folder
WEEK="$(date -u +%Y-W%V)"
OUTPUT_BASE="${FACTORY_OUTPUT:-$FACTORY/output}"
WEEK_DIR="$OUTPUT_BASE/$WEEK"
STATE_FILE="$WEEK_DIR/pipeline.state"
mkdir -p "$WEEK_DIR"

# Initialize pipeline.state if needed
if [ ! -f "$STATE_FILE" ]; then
  jq -n --arg week "$WEEK" --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{week:$week, created:$now, stages:{research:{status:"pending"},strategy:{status:"pending"},writing:{status:"pending"},visuals:{status:"pending"},publishing:{status:"pending"},analytics:{status:"pending"},evolution:{status:"pending"}}}' \
    > "$STATE_FILE"
fi

# Gather KPI data (last 4 weeks)
KPI_DATA=""
if [ -f "$ANALYTICS/kpi.jsonl" ]; then
  KPI_DATA="$(tail -200 "$ANALYTICS/kpi.jsonl")"
fi

if [ -z "$KPI_DATA" ]; then
  echo "No KPI data found. Log post metrics with /factory log first."
  echo "Usage: /factory log <post-id> impressions=N engagements=N clicks=N"
  exit 0
fi

# Gather context
PERSONA="$(cat "$CONFIG/persona.yml")"
PILLARS="$(cat "$CONFIG/pillars.yml")"

# Gather weekly summaries if they exist
WEEKLY_HISTORY=""
if [ -f "$ANALYTICS/weekly_summary.jsonl" ]; then
  WEEKLY_HISTORY="$(tail -10 "$ANALYTICS/weekly_summary.jsonl")"
fi

USER_MSG="## Persona
$PERSONA

## Content Pillars
$PILLARS

## KPI Data (recent posts)
$KPI_DATA"

if [ -n "$WEEKLY_HISTORY" ]; then
  USER_MSG="$USER_MSG

## Historical Weekly Summaries
$WEEKLY_HISTORY"
fi

USER_MSG="$USER_MSG

Analyze this performance data. Identify what's working, what isn't, and recommend specific changes to the persona, pillars, and content strategy. Be data-driven and specific."

# Inject directive if present
DIRECTIVE_FILE="${FACTORY_DIRECTIVES:-$FACTORY/directives}/analytics.md"
if [ -s "$DIRECTIVE_FILE" ]; then
  USER_MSG="$USER_MSG

## Current Directive (from operator)
$(cat "$DIRECTIVE_FILE")"
fi

TMP_OUT="/tmp/factory_analytics_result.txt"
openclaw agent --agent factory-analytics --local \
  --message "$USER_MSG" --timeout 600 --json \
  >>"$TMP_OUT" 2>&1
EXIT_CODE=$?
JSON_OUT="$(sed -n '/^{/,$p' "$TMP_OUT")"
if [ $EXIT_CODE -ne 0 ] || [ -z "$JSON_OUT" ]; then
  echo "ERROR: factory-analytics subagent failed (exit $EXIT_CODE)" >&2
  tail -5 "$TMP_OUT" >&2
  exit 1
fi
RESULT="$(echo "$JSON_OUT" | jq -r '.payloads[0].text // empty')"
if [ -z "$RESULT" ]; then
  echo "ERROR: factory-analytics returned empty response" >&2
  exit 1
fi

{ printf -- "---\nweek: %s\ndate: %s\ntype: analytics\ntags: [factory]\n---\n\n" \
    "$WEEK" "$(date -u +%Y-%m-%d)"; echo "$RESULT"; } > "$WEEK_DIR/report.md"

# Update pipeline state
TMP="$(mktemp)"
jq --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '.stages.analytics = {status:"done", completed:$now}' "$STATE_FILE" > "$TMP"
mv "$TMP" "$STATE_FILE"

echo "Analytics report complete for $WEEK. Output: $WEEK_DIR/report.md"
