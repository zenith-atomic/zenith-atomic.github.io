#!/usr/bin/env bash
set -euo pipefail

FACTORY="$HOME/.openclaw/workspace/factory"
SCRIPTS="$FACTORY/scripts"
AGENTS="$FACTORY/agents"
INBOX_DIR="$FACTORY/inbox"

if [ "$#" -lt 1 ]; then
  echo "Usage: inbox_add.sh <url_or_text> [tag1,tag2]" >&2
  exit 1
fi

INPUT="$1"
TAGS="${2:-}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%S)"
DATE_ISO="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
DATE_SHORT="$(date -u +%Y-%m-%d)"

mkdir -p "$INBOX_DIR"

# Detect URL vs plain text
if echo "$INPUT" | grep -qE '^https?://'; then
  TYPE="url"
  SOURCE_URL="$INPUT"

  # Fetch page content
  FETCH_RESULT="$(python3 "$SCRIPTS/inbox_fetch.py" "$INPUT" 2>/dev/null || echo '{"error":"fetch failed","title":"","text":""}')"
  FETCH_ERROR="$(echo "$FETCH_RESULT" | jq -r '.error // empty')"
  if [ -n "$FETCH_ERROR" ]; then
    echo "WARNING: Could not fetch URL ($FETCH_ERROR) — saving link only" >&2
    TITLE="$(echo "$INPUT" | sed 's|https\?://||; s|/.*||')"
    BODY_TEXT="[Could not fetch content: $FETCH_ERROR]"
  else
    TITLE="$(echo "$FETCH_RESULT" | jq -r '.title')"
    BODY_TEXT="$(echo "$FETCH_RESULT" | jq -r '.text')"
  fi

  # Generate summary via LLM if we have content
  if [ "$BODY_TEXT" != "[Could not fetch content: $FETCH_ERROR]" ] && [ -n "${OPENAI_API_KEY:-}" ]; then
    SUMMARY="$("$SCRIPTS/call_agent.sh" "$AGENTS/inbox_summarize.prompt" "$BODY_TEXT" "gpt-5.4-mini" "300" 2>/dev/null || echo "[Summary unavailable]")"
  else
    SUMMARY="[Summary unavailable]"
  fi

  DEFAULT_TAGS="reference"
else
  TYPE="text"
  SOURCE_URL=""
  TITLE="$(echo "$INPUT" | head -c 60 | tr '\n' ' ' | xargs)"
  BODY_TEXT="$INPUT"
  SUMMARY="$INPUT"
  DEFAULT_TAGS="inspiration"
fi

# Build tag list
if [ -n "$TAGS" ]; then
  TAG_LIST="[$(echo "$TAGS" | sed 's/,/, /g')]"
else
  TAG_LIST="[$DEFAULT_TAGS]"
fi

# Build slug from title
SLUG="$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g; s/--*/-/g; s/^-//; s/-$//' | head -c 40)"
[ -z "$SLUG" ] && SLUG="note"

FILENAME="${DATE_SHORT}-${SLUG}.md"
FILEPATH="$INBOX_DIR/$FILENAME"

# Write the inbox file
{
  printf "---\n"
  printf "id: inbox-%s\n" "$TIMESTAMP"
  printf "date: %s\n" "$DATE_ISO"
  printf "type: %s\n" "$TYPE"
  [ -n "$SOURCE_URL" ] && printf "source_url: %s\n" "$SOURCE_URL"
  printf "title: %q\n" "$TITLE"
  printf "tags: %s\n" "$TAG_LIST"
  printf "status: active\n"
  printf "used_in: []\n"
  printf "added_by: cli\n"
  printf "---\n\n"
  printf "## Summary\n\n%s\n\n" "$SUMMARY"
  if [ "$TYPE" = "url" ] && [ -n "$BODY_TEXT" ]; then
    printf "## Content\n\n%s\n" "$BODY_TEXT"
  fi
} > "$FILEPATH"

echo "Saved: $TITLE → inbox/$FILENAME"
