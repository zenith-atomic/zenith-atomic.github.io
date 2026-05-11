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

# Require strategy to be done
if [ ! -f "$WEEK_DIR/strategy.md" ]; then
  echo "ERROR: strategy.md not found. Run /factory strategy first." >&2
  exit 1
fi

mkdir -p "$WEEK_DIR/drafts"

# Gather context
PERSONA="$(cat "$CONFIG/persona.yml")"
PLATFORMS="$(cat "$CONFIG/platforms.yml")"
STRATEGY="$(cat "$WEEK_DIR/strategy.md")"

USER_MSG="## Persona & Voice
$PERSONA

## Platform Specs
$PLATFORMS

## Weekly Strategy & Content Briefs
$STRATEGY

Write ALL posts listed in the content calendar above. For each post, provide 3 hook variants, the full body, a CTA, and a visual note. Format each post with a clear header showing the post number, platform, and format."

# Inject directive if present
DIRECTIVE_FILE="${FACTORY_DIRECTIVES:-$FACTORY/directives}/writer.md"
if [ -s "$DIRECTIVE_FILE" ]; then
  USER_MSG="$USER_MSG

## Current Directive (from operator)
$(cat "$DIRECTIVE_FILE")"
fi

# Single call with full strategy — writer needs longer timeout for full 20-post output
TMP_OUT="/tmp/factory_writer_result.txt"
openclaw agent --agent factory-writer --local \
  --message "$USER_MSG" --timeout 900 --json \
  >>"$TMP_OUT" 2>&1
EXIT_CODE=$?
JSON_OUT="$(sed -n '/^{/,$p' "$TMP_OUT")"
if [ $EXIT_CODE -ne 0 ] || [ -z "$JSON_OUT" ]; then
  echo "ERROR: factory-writer subagent failed (exit $EXIT_CODE)" >&2
  tail -5 "$TMP_OUT" >&2
  exit 1
fi
RESULT="$(echo "$JSON_OUT" | jq -r '.payloads[0].text // empty')"

# Validate output is substantive before saving
if [ "${#RESULT}" -lt 500 ]; then
  echo "ERROR: writer output too short (${#RESULT} chars) — likely truncated or empty response:" >&2
  echo "$RESULT" >&2
  exit 1
fi

# Write all drafts to a single file
printf -- "---\nweek: %s\ndate: %s\ntype: drafts\ntags: [factory, drafts]\n---\n\n" \
  "$WEEK" "$(date -u +%Y-%m-%d)" | cat - <(echo "$RESULT") > "$WEEK_DIR/drafts/all_drafts.md"

# Split into individual files — robust pattern matching multiple LLM formatting styles
POST_NUM=0
CURRENT_FILE=""
while IFS= read -r line; do
  if echo "$line" | grep -qiE '^#{1,3} *Post [0-9]+'; then
    POST_NUM=$((POST_NUM + 1))
    PLATFORM="$(echo "$line" | grep -oiE 'twitter|instagram|linkedin|youtube|tiktok' \
      | head -1 | tr '[:upper:]' '[:lower:]' || echo "general")"
    CURRENT_FILE="$WEEK_DIR/drafts/$(printf '%03d' "$POST_NUM")-${PLATFORM}.md"
    echo "$line" > "$CURRENT_FILE"
  elif [ -n "$CURRENT_FILE" ]; then
    echo "$line" >> "$CURRENT_FILE"
  fi
done <<< "$RESULT"

# Update pipeline state
if [ -f "$STATE_FILE" ]; then
  TMP="$(mktemp)"
  jq --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '.stages.writing = {status:"done", completed:$now}' "$STATE_FILE" > "$TMP"
  mv "$TMP" "$STATE_FILE"
fi

echo "Writing complete for $WEEK. $POST_NUM drafts in $WEEK_DIR/drafts/"
