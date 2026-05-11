#!/usr/bin/env bash
set -euo pipefail

# LLM-assisted review: send recent notes to OpenAI API for intelligent fact extraction.
# Requires OPENAI_API_KEY environment variable.

WORKDIR="/home/ai/.openclaw/workspace"
NOTES="$WORKDIR/state/active_notes.log"
MEMORY="$WORKDIR/memory/MEMORY.md"
MAX_NOTES=20

if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "Error: OPENAI_API_KEY not set."
  echo "Set it with: export OPENAI_API_KEY=sk-..."
  exit 1
fi

if [ ! -f "$NOTES" ]; then
  echo "No notes to review."
  exit 0
fi

# Collect last N non-comment lines from notes
RECENT="$(grep -v '^#' "$NOTES" | tail -n "$MAX_NOTES")"
if [ -z "$RECENT" ]; then
  echo "No notes to review."
  exit 0
fi

# Collect current MEMORY.md for dedup context
CURRENT_MEMORY="$(cat "$MEMORY")"

# Build the prompt
SYSTEM_PROMPT="You are a memory curator. Given recent session notes and existing durable memory, extract new durable facts worth remembering long-term. Output ONLY facts that are:
- About the user's preferences, decisions, project state, or system changes
- Specific and factual (not vague status updates)
- Not already captured in the existing memory
- Not test entries or implementation details

Output one fact per line, no bullets or numbering. If no new facts found, output: (none)"

USER_PROMPT="Existing memory:
$CURRENT_MEMORY

Recent notes:
$RECENT"

# Call OpenAI API
RESPONSE="$(curl -sS https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n \
    --arg sys "$SYSTEM_PROMPT" \
    --arg usr "$USER_PROMPT" \
    '{
      model: "gpt-4.1-mini",
      messages: [
        {role: "system", content: $sys},
        {role: "user", content: $usr}
      ],
      temperature: 0.3,
      max_tokens: 500
    }')" 2>&1)"

# Extract the response text
FACTS="$(echo "$RESPONSE" | jq -r '.choices[0].message.content // empty' 2>/dev/null)"

if [ -z "$FACTS" ]; then
  ERROR="$(echo "$RESPONSE" | jq -r '.error.message // empty' 2>/dev/null)"
  if [ -n "$ERROR" ]; then
    echo "API error: $ERROR"
  else
    echo "No response from API."
  fi
  exit 1
fi

echo "=== LLM-extracted candidates ==="
echo "$FACTS"
echo ""
echo "Use /fact <text> to promote any of these."
