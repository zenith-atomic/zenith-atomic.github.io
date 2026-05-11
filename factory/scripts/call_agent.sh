#!/usr/bin/env bash
set -euo pipefail
# Shared LLM caller for content factory subagents
# Usage: call_agent.sh <prompt_file> <user_message> [model] [max_tokens] [temperature]

PROMPT_FILE="$1"
USER_MSG="$2"
MODEL="${3:-gpt-4.1-mini}"
MAX_TOKENS="${4:-2000}"
TEMP="${5:-0.7}"

if [ ! -f "$PROMPT_FILE" ]; then
  echo "ERROR: prompt file not found: $PROMPT_FILE" >&2
  exit 1
fi

if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "ERROR: OPENAI_API_KEY not set" >&2
  exit 1
fi

SYSTEM_PROMPT="$(cat "$PROMPT_FILE")"

CURL_ERR="$(mktemp)"
HTTP_RESPONSE="$(curl -sS -w "\n%{http_code}" --max-time 120 \
  https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n \
    --arg sys "$SYSTEM_PROMPT" \
    --arg usr "$USER_MSG" \
    --arg model "$MODEL" \
    --argjson max "$MAX_TOKENS" \
    --argjson temp "$TEMP" \
    '{model:$model, messages:[{role:"system",content:$sys},{role:"user",content:$usr}], temperature:$temp, max_tokens:$max}')" \
  2>"$CURL_ERR")"

HTTP_CODE="$(echo "$HTTP_RESPONSE" | tail -1)"
BODY="$(echo "$HTTP_RESPONSE" | head -n -1)"

if [ -s "$CURL_ERR" ]; then
  echo "ERROR: curl transport error:" >&2
  cat "$CURL_ERR" >&2
fi
rm -f "$CURL_ERR"

if [ "$HTTP_CODE" != "200" ]; then
  ERROR_MSG="$(echo "$BODY" | jq -r '.error.message // .error // "unknown"' 2>/dev/null || echo "$BODY")"
  echo "ERROR: HTTP $HTTP_CODE — $ERROR_MSG" >&2
  exit 1
fi

CONTENT="$(echo "$BODY" | jq -r '.choices[0].message.content // empty' 2>/dev/null)"
if [ -z "$CONTENT" ]; then
  FINISH="$(echo "$BODY" | jq -r '.choices[0].finish_reason // "unknown"' 2>/dev/null)"
  echo "ERROR: empty content from API (finish_reason: $FINISH)" >&2
  echo "Full response: $BODY" >&2
  exit 1
fi

echo "$CONTENT"
