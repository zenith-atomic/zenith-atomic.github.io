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

# Require drafts + visuals
if [ ! -f "$WEEK_DIR/drafts/all_drafts.md" ]; then
  echo "ERROR: drafts not found. Run /factory write first." >&2
  exit 1
fi

# Gather context
PERSONA="$(cat "$CONFIG/persona.yml")"
SCHEDULE="$(cat "$CONFIG/schedule.yml")"
PLATFORMS="$(cat "$CONFIG/platforms.yml")"
DRAFTS="$(cat "$WEEK_DIR/drafts/all_drafts.md")"

VISUALS=""
if [ -f "$WEEK_DIR/visuals/all_visuals.md" ]; then
  VISUALS="$(cat "$WEEK_DIR/visuals/all_visuals.md")"
fi

USER_MSG="## Persona
$PERSONA

## Posting Schedule
$SCHEDULE

## Platform Specs
$PLATFORMS

## Approved Drafts
$DRAFTS"

if [ -n "$VISUALS" ]; then
  USER_MSG="$USER_MSG

## Visual Specs
$VISUALS"
fi

USER_MSG="$USER_MSG

Format all content as copy-paste ready for each platform. Generate a detailed posting checklist with dates and times. Use the best hook variant for each post."

# Inject directive if present
DIRECTIVE_FILE="${FACTORY_DIRECTIVES:-$FACTORY/directives}/publisher.md"
if [ -s "$DIRECTIVE_FILE" ]; then
  USER_MSG="$USER_MSG

## Current Directive (from operator)
$(cat "$DIRECTIVE_FILE")"
fi

TMP_OUT="/tmp/factory_publisher_result.txt"
openclaw agent --agent factory-publisher --local \
  --message "$USER_MSG" --timeout 600 --json \
  >>"$TMP_OUT" 2>&1
EXIT_CODE=$?
JSON_OUT="$(sed -n '/^{/,$p' "$TMP_OUT")"
if [ $EXIT_CODE -ne 0 ] || [ -z "$JSON_OUT" ]; then
  echo "ERROR: factory-publisher subagent failed (exit $EXIT_CODE)" >&2
  tail -5 "$TMP_OUT" >&2
  exit 1
fi
RESULT="$(echo "$JSON_OUT" | jq -r '.payloads[0].text // empty')"
if [ -z "$RESULT" ]; then
  echo "ERROR: factory-publisher returned empty response" >&2
  exit 1
fi

{ printf -- "---\nweek: %s\ndate: %s\ntype: publishing\ntags: [factory]\n---\n\n" \
    "$WEEK" "$(date -u +%Y-%m-%d)"; echo "$RESULT"; } > "$WEEK_DIR/publishing_checklist.md"

# Initialize published.log
if [ ! -f "$WEEK_DIR/published.log" ]; then
  echo "# Published Log — $WEEK" > "$WEEK_DIR/published.log"
  echo "# Format: YYYY-MM-DDTHH:MM:SSZ | platform | post_id | status" >> "$WEEK_DIR/published.log"
fi

# Update pipeline state
TMP="$(mktemp)"
jq --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '.stages.publishing = {status:"done", completed:$now}' "$STATE_FILE" > "$TMP"
mv "$TMP" "$STATE_FILE"

echo "Publishing checklist ready for $WEEK. Output: $WEEK_DIR/publishing_checklist.md"
