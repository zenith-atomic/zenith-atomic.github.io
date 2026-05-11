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

# Require drafts to exist
if [ ! -f "$WEEK_DIR/drafts/all_drafts.md" ]; then
  echo "ERROR: drafts not found. Run /factory write first." >&2
  exit 1
fi

mkdir -p "$WEEK_DIR/visuals"

# Gather context
PERSONA="$(cat "$CONFIG/persona.yml")"
PLATFORMS="$(cat "$CONFIG/platforms.yml")"
DRAFTS="$(cat "$WEEK_DIR/drafts/all_drafts.md")"

USER_MSG="## Persona & Visual Identity
$PERSONA

## Platform Specs
$PLATFORMS

## Content Drafts
$DRAFTS

Generate image prompts and visual direction for each post that needs visuals. Focus on posts for Instagram, LinkedIn, YouTube, and TikTok. Twitter posts only need visuals if they'd significantly boost engagement."

# Inject directive if present
DIRECTIVE_FILE="${FACTORY_DIRECTIVES:-$FACTORY/directives}/creative.md"
if [ -s "$DIRECTIVE_FILE" ]; then
  USER_MSG="$USER_MSG

## Current Directive (from operator)
$(cat "$DIRECTIVE_FILE")"
fi

TMP_OUT="/tmp/factory_creative_result.txt"
: > "$TMP_OUT"
openclaw agent --agent factory-creative --local \
  --message "$USER_MSG" --timeout 600 --json \
  >>"$TMP_OUT" 2>&1
EXIT_CODE=$?
JSON_OUT="$(sed -n '/^{/,$p' "$TMP_OUT")"
if [ $EXIT_CODE -ne 0 ] || [ -z "$JSON_OUT" ]; then
  echo "ERROR: factory-creative subagent failed (exit $EXIT_CODE)" >&2
  tail -5 "$TMP_OUT" >&2
  exit 1
fi
RESULT="$(echo "$JSON_OUT" | jq -r '.payloads[0].text // empty')"
if [ -z "$RESULT" ]; then
  echo "ERROR: factory-creative returned empty response" >&2
  exit 1
fi

{ printf -- "---\nweek: %s\ndate: %s\ntype: visuals\ntags: [factory]\n---\n\n" \
    "$WEEK" "$(date -u +%Y-%m-%d)"; echo "$RESULT"; } > "$WEEK_DIR/visuals/all_visuals.md"

# Update pipeline state
TMP="$(mktemp)"
jq --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '.stages.visuals = {status:"done", completed:$now}' "$STATE_FILE" > "$TMP"
mv "$TMP" "$STATE_FILE"

echo "Visuals complete for $WEEK. Output: $WEEK_DIR/visuals/all_visuals.md"
