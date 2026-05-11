#!/usr/bin/env bash
set -euo pipefail

FACTORY="$HOME/.openclaw/workspace/factory"
SCRIPTS="$FACTORY/scripts"
AGENTS="$FACTORY/agents"
CONFIG="$FACTORY/config"
ANALYTICS="$FACTORY/analytics"

# Resolve current week
WEEK="$(date -u +%Y-W%V)"
WEEK_DIR="$FACTORY/output/$WEEK"
STATE_FILE="$WEEK_DIR/pipeline.state"

# Require analytics report
if [ ! -f "$WEEK_DIR/report.md" ]; then
  echo "ERROR: report.md not found. Run /factory analyze first." >&2
  exit 1
fi

PERSONA="$(cat "$CONFIG/persona.yml")"
REPORT="$(cat "$WEEK_DIR/report.md")"

# Snapshot current persona before mutation
SNAPSHOT="$(cat "$CONFIG/persona.yml")"

USER_MSG="## Current Persona Config
$PERSONA

## This Week's Analytics Report
$REPORT

Based on the analytics report, output an UPDATED persona.yml that incorporates the performance data. Specifically:
1. Move confirmed successful hook styles from styles_to_test to styles_that_work
2. Update best_formats, best_topics, best_post_times from the data
3. Adjust topic weights if the data suggests certain topics perform better
4. Update avg_engagement_rate
5. Add any new hook styles worth testing
6. Keep the YAML structure exactly the same — only change values

Output ONLY the complete YAML content, no markdown fences, no commentary."

RESULT="$("$SCRIPTS/call_agent.sh" "$AGENTS/analytics.prompt" "$USER_MSG" "gpt-5.4-mini" "2000" "0.3")"

# Validate the result looks like YAML (basic check)
if ! echo "$RESULT" | grep -q "^version:"; then
  echo "ERROR: LLM did not return valid persona YAML. Aborting evolution." >&2
  echo "Raw output saved to $WEEK_DIR/evolution_attempt.txt" >&2
  echo "$RESULT" > "$WEEK_DIR/evolution_attempt.txt"
  exit 1
fi

# Strip any markdown fences if present
CLEAN_RESULT="$(echo "$RESULT" | sed '/^```/d')"

# Write updated persona
echo "$CLEAN_RESULT" > "$CONFIG/persona.yml"

# Log the evolution
mkdir -p "$ANALYTICS"
{
  echo "---"
  echo "date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "week: $WEEK"
  echo "trigger: analytics-driven"
  echo ""
  echo "### Changes"
  diff <(echo "$SNAPSHOT") <(echo "$CLEAN_RESULT") || true
  echo ""
} >> "$ANALYTICS/evolution.log"

# Update pipeline state
if [ -f "$STATE_FILE" ]; then
  TMP="$(mktemp)"
  jq --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '.stages.evolution = {status:"done", completed:$now}' "$STATE_FILE" > "$TMP"
  mv "$TMP" "$STATE_FILE"
fi

echo "Persona evolved for $WEEK. Changes logged to analytics/evolution.log"
