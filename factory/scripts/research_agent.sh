#!/usr/bin/env bash
set -euo pipefail

FACTORY="$HOME/.openclaw/workspace/factory"
SCRIPTS="$FACTORY/scripts"
AGENTS="$FACTORY/agents"
CONFIG="${FACTORY_CONFIG:-$FACTORY/config}"
FOCUS="${1:-}"

# Resolve current week folder
WEEK="$(date -u +%Y-W%V)"
OUTPUT_BASE="${FACTORY_OUTPUT:-$FACTORY/output}"
WEEK_DIR="$OUTPUT_BASE/$WEEK"
mkdir -p "$WEEK_DIR"

# Live log for dashboard preview
LIVE_LOG="$WEEK_DIR/research.log"
printf "[%s] Scout initializing...\n" "$(date -u +%H:%M:%SZ)" > "$LIVE_LOG"

# Initialize pipeline.state if needed
STATE_FILE="$WEEK_DIR/pipeline.state"
if [ ! -f "$STATE_FILE" ]; then
  jq -n --arg week "$WEEK" --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{week:$week, created:$now, stages:{research:{status:"pending"},strategy:{status:"pending"},writing:{status:"pending"},visuals:{status:"pending"},publishing:{status:"pending"},analytics:{status:"pending"},evolution:{status:"pending"}}}' \
    > "$STATE_FILE"
fi

# Build user message with full context
PERSONA="$(cat "$CONFIG/persona.yml")"
PILLARS="$(cat "$CONFIG/pillars.yml")"
PLATFORMS="$(cat "$CONFIG/platforms.yml")"

printf "[%s] Loading persona, pillars, and platform config...\n" "$(date -u +%H:%M:%SZ)" >> "$LIVE_LOG"

USER_MSG="## Persona
$PERSONA

## Content Pillars
$PILLARS

## Target Platforms
$PLATFORMS"

if [ -n "$FOCUS" ]; then
  USER_MSG="$USER_MSG

## Focus Topic
$FOCUS"
fi

USER_MSG="$USER_MSG

Analyze the competitive landscape for this persona. Focus on their topic space across the listed platforms. Identify what's working right now, what gaps exist, and what hooks are performing best."

# Inject directive last so it takes priority over default task
DIRECTIVE_FILE="${FACTORY_DIRECTIVES:-$FACTORY/directives}/research.md"
if [ -s "$DIRECTIVE_FILE" ]; then
  USER_MSG="$USER_MSG

## Current Directive (from operator)
$(cat "$DIRECTIVE_FILE")"
fi

# Inject inbox reference material if available
INBOX_DIR="${FACTORY_INBOX:-$FACTORY/inbox}"
if [ -d "$INBOX_DIR" ]; then
  INBOX_ITEMS="$(find "$INBOX_DIR" -name '*.md' -mtime -30 \
    -exec grep -l 'status: active' {} \; 2>/dev/null \
    | sort -r | head -10 | xargs cat 2>/dev/null || true)"
  if [ -n "$INBOX_ITEMS" ]; then
    USER_MSG="$USER_MSG

## Saved Reference Material (from inbox — use these as inspiration and reference)
$INBOX_ITEMS"
  fi
fi

# Spawn research subagent via OpenClaw (Steel browser for live research, bypasses DuckDuckGo bot detection)
# NOTE: openclaw agent --json writes JSON to stderr alongside diagnostics; stdout captures any streaming text
printf "[%s] Calling Scout agent (timeout: 30min)...\n" "$(date -u +%H:%M:%SZ)" >> "$LIVE_LOG"
TMP_OUT="/tmp/factory_research_result.txt"
openclaw agent --agent factory-research --local \
  --message "$USER_MSG" --timeout 1800 --json 2>>"$LIVE_LOG" | tee "$TMP_OUT"
EXIT_CODE=$?
JSON_OUT="$(sed -n '/^{/,$p' "$TMP_OUT")"
if [ $EXIT_CODE -ne 0 ] || [ -z "$JSON_OUT" ]; then
  printf "[%s] ERROR: Scout failed (exit %s)\n" "$(date -u +%H:%M:%SZ)" "$EXIT_CODE" >> "$LIVE_LOG"
  echo "ERROR: factory-research subagent failed (exit $EXIT_CODE)" >&2
  tail -5 "$TMP_OUT" >&2
  mkdir -p "$FACTORY/analytics"
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) | research | FAILED | exit=$EXIT_CODE" \
    >> "$FACTORY/analytics/pipeline.log"
  exit 1
fi
RESULT="$(echo "$JSON_OUT" | jq -r '.payloads[0].text // empty')"
if [ -z "$RESULT" ]; then
  echo "ERROR: factory-research returned empty response" >&2
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) | research | FAILED | empty response from subagent" \
    >> "$FACTORY/analytics/pipeline.log"
  exit 1
fi

# Write output with frontmatter
printf -- "---\nweek: %s\ndate: %s\ntype: research\ntags: [factory, research]\n---\n\n" \
  "$WEEK" "$(date -u +%Y-%m-%d)" | cat - <(echo "$RESULT") > "$WEEK_DIR/research.md"

# Update pipeline state
TMP="$(mktemp)"
jq --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '.stages.research = {status:"done", completed:$now}' "$STATE_FILE" > "$TMP"
mv "$TMP" "$STATE_FILE"

printf "[%s] Research complete. Output saved to research.md\n" "$(date -u +%H:%M:%SZ)" >> "$LIVE_LOG"
echo "Research complete for $WEEK. Output: $WEEK_DIR/research.md"
