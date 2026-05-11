#!/usr/bin/env bash
set -euo pipefail

FACTORY="$HOME/.openclaw/workspace/factory"
SCRIPTS="$FACTORY/scripts"
AGENTS="$FACTORY/agents"
CONFIG="${FACTORY_CONFIG:-$FACTORY/config}"

# Resolve current week folder
WEEK="$(date -u +%Y-W%V)"
OUTPUT_BASE="${FACTORY_OUTPUT:-$FACTORY/output}"
WEEK_DIR="$OUTPUT_BASE/$WEEK"
STATE_FILE="$WEEK_DIR/pipeline.state"

# Require research to be done
if [ ! -f "$WEEK_DIR/research.md" ]; then
  echo "ERROR: research.md not found. Run /factory research first." >&2
  exit 1
fi

# Gather context
PERSONA="$(cat "$CONFIG/persona.yml")"
PILLARS="$(cat "$CONFIG/pillars.yml")"
SCHEDULE="$(cat "$CONFIG/schedule.yml")"
PLATFORMS="$(cat "$CONFIG/platforms.yml")"
RESEARCH="$(cat "$WEEK_DIR/research.md")"

# Check for last week's analytics report
LAST_WEEK="$(date -u -d '7 days ago' +%Y-W%V)"
LAST_REPORT=""
if [ -f "$OUTPUT_BASE/$LAST_WEEK/report.md" ]; then
  LAST_REPORT="$(cat "$OUTPUT_BASE/$LAST_WEEK/report.md")"
fi

USER_MSG="## Persona
$PERSONA

## Content Pillars
$PILLARS

## Posting Schedule
$SCHEDULE

## Platform Specs
$PLATFORMS

## This Week's Research
$RESEARCH"

if [ -n "$LAST_REPORT" ]; then
  USER_MSG="$USER_MSG

## Last Week's Analytics Report
$LAST_REPORT"
fi

# Inject directive if present
DIRECTIVE_FILE="${FACTORY_DIRECTIVES:-$FACTORY/directives}/strategy.md"
if [ -s "$DIRECTIVE_FILE" ]; then
  USER_MSG="$USER_MSG

## Current Directive (from operator)
$(cat "$DIRECTIVE_FILE")"
fi

USER_MSG="$USER_MSG

Create a detailed weekly content plan based on this research and data. Assign specific content to each day, matching the posting schedule. Include test hypotheses."

# Inject inbox inspiration material if available
INBOX_DIR="${FACTORY_INBOX:-$FACTORY/inbox}"
if [ -d "$INBOX_DIR" ]; then
  INBOX_ITEMS="$(find "$INBOX_DIR" -name '*.md' -mtime -30 \
    -exec grep -l 'status: active' {} \; 2>/dev/null \
    | sort -r | head -8 | xargs cat 2>/dev/null || true)"
  if [ -n "$INBOX_ITEMS" ]; then
    USER_MSG="$USER_MSG

## Saved Content Ideas & References (from inbox — consider these when planning posts)
$INBOX_ITEMS"
  fi
fi

TMP_OUT="/tmp/factory_strategy_result.txt"
openclaw agent --agent factory-strategy --local \
  --message "$USER_MSG" --timeout 600 --json \
  >>"$TMP_OUT" 2>&1
EXIT_CODE=$?
JSON_OUT="$(sed -n '/^{/,$p' "$TMP_OUT")"
if [ $EXIT_CODE -ne 0 ] || [ -z "$JSON_OUT" ]; then
  echo "ERROR: factory-strategy subagent failed (exit $EXIT_CODE)" >&2
  tail -5 "$TMP_OUT" >&2
  exit 1
fi
RESULT="$(echo "$JSON_OUT" | jq -r '.payloads[0].text // empty')"
if [ -z "$RESULT" ]; then
  echo "ERROR: factory-strategy returned empty response" >&2
  exit 1
fi

printf -- "---\nweek: %s\ndate: %s\ntype: strategy\ntags: [factory, strategy]\n---\n\n" \
  "$WEEK" "$(date -u +%Y-%m-%d)" | cat - <(echo "$RESULT") > "$WEEK_DIR/strategy.md"

# Update pipeline state
TMP="$(mktemp)"
jq --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '.stages.strategy = {status:"done", completed:$now}' "$STATE_FILE" > "$TMP"
mv "$TMP" "$STATE_FILE"

echo "Strategy complete for $WEEK. Output: $WEEK_DIR/strategy.md"
