#!/usr/bin/env bash
# Post a YouTube Community post via YouTube Data API v3
# Requires: YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN, YOUTUBE_CHANNEL_ID
# NOTE: Community posts require 500+ subscribers and are text/image only (no video upload)
set -euo pipefail

if [ "${1:-}" = "" ]; then
  echo "Usage: post_youtube.sh <post-json-file>" >&2
  exit 1
fi

POST_FILE="$1"
if [ ! -f "$POST_FILE" ]; then
  echo "ERROR: post file not found: $POST_FILE" >&2
  exit 1
fi

if [ -f "$HOME/.openclaw/.env" ]; then
  set +u; source "$HOME/.openclaw/.env"; set -u
fi

CONTENT="$(jq -r '.content // ""' "$POST_FILE")"
if [ -z "$CONTENT" ]; then
  echo "ERROR: post content is empty" >&2
  exit 1
fi

: "${YOUTUBE_REFRESH_TOKEN:?YOUTUBE_REFRESH_TOKEN not set}"
: "${YOUTUBE_CHANNEL_ID:?YOUTUBE_CHANNEL_ID not set}"
: "${YOUTUBE_CLIENT_ID:?YOUTUBE_CLIENT_ID not set}"
: "${YOUTUBE_CLIENT_SECRET:?YOUTUBE_CLIENT_SECRET not set}"

# --- Refresh access token ---
TOKEN_RESP="$(curl -sS --max-time 15 \
  "https://oauth2.googleapis.com/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=${YOUTUBE_CLIENT_ID}&client_secret=${YOUTUBE_CLIENT_SECRET}&refresh_token=${YOUTUBE_REFRESH_TOKEN}&grant_type=refresh_token" \
  2>/dev/null)"

ACCESS_TOKEN="$(echo "$TOKEN_RESP" | jq -r '.access_token // empty')"
if [ -z "$ACCESS_TOKEN" ]; then
  echo "ERROR: YouTube token refresh failed: $(echo "$TOKEN_RESP" | jq -r '.error_description // .error // .')" >&2
  exit 1
fi

# --- Optional image attachment ---
IMAGE_URL="$(jq -r '.image_url // ""' "$POST_FILE")"

if [ -n "$IMAGE_URL" ]; then
  # Community posts with images use a different endpoint (postImages first, then reference)
  # For simplicity: post text + link if image URL is provided
  CONTENT="${CONTENT}

${IMAGE_URL}"
fi

# --- Post community post via YouTube Data API v3 ---
# Community posts use the `communityPosts` resource
PAYLOAD="$(jq -n \
  --arg text "$CONTENT" \
  '{
    snippet: {
      type: "textPost",
      textOriginalContent: $text
    }
  }')"

RESP="$(curl -sS --max-time 30 \
  -X POST "https://www.googleapis.com/youtube/v3/communityPosts?part=snippet,status" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  2>/dev/null)"

if echo "$RESP" | jq -e '.error' > /dev/null 2>&1; then
  ERR="$(echo "$RESP" | jq -r '.error.message // .error')"
  CODE="$(echo "$RESP" | jq -r '.error.code // 0')"
  echo "ERROR: YouTube API $CODE: $ERR" >&2
  # Common: 403 if channel has < 500 subscribers or community posts not enabled
  if [ "$CODE" = "403" ]; then
    echo "NOTE: Community posts require 500+ subscribers. Channel ID: $YOUTUBE_CHANNEL_ID" >&2
  fi
  exit 1
fi

POST_ID="$(echo "$RESP" | jq -r '.id // empty')"
if [ -z "$POST_ID" ]; then
  echo "ERROR: No post ID in YouTube response" >&2
  echo "Response: $RESP" >&2
  exit 1
fi

echo "https://www.youtube.com/post/${POST_ID}"
