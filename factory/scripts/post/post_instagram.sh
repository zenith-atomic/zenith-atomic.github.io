#!/usr/bin/env bash
# Post to Instagram via Graph API (two-step: create container → publish)
# Requires: META_APP_ID, META_APP_SECRET, INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_USER_ID
set -euo pipefail

if [ "${1:-}" = "" ]; then
  echo "Usage: post_instagram.sh <post-json-file>" >&2
  exit 1
fi

POST_FILE="$1"
if [ ! -f "$POST_FILE" ]; then
  echo "ERROR: post file not found: $POST_FILE" >&2
  exit 1
fi

# Load credentials from .env if not already set
if [ -f "$HOME/.openclaw/.env" ]; then
  set +u; source "$HOME/.openclaw/.env"; set -u
fi

CONTENT="$(jq -r '.content // ""' "$POST_FILE")"
if [ -z "$CONTENT" ]; then
  echo "ERROR: post content is empty" >&2
  exit 1
fi

: "${INSTAGRAM_ACCESS_TOKEN:?INSTAGRAM_ACCESS_TOKEN not set}"
: "${INSTAGRAM_USER_ID:?INSTAGRAM_USER_ID not set}"

# Optional: image URL for carousel or single image post
IMAGE_URL="$(jq -r '.image_url // ""' "$POST_FILE")"
FORMAT="$(jq -r '.format // "single"' "$POST_FILE")"

# Auto-refresh token if within 7 days of expiry (requires META_APP_ID + META_APP_SECRET)
EXPIRY="${INSTAGRAM_TOKEN_EXPIRY:-0}"
NOW_TS="$(date -u +%s)"
SEVEN_DAYS=$((7 * 86400))
if [ -n "${META_APP_ID:-}" ] && [ -n "${META_APP_SECRET:-}" ] && [ "$EXPIRY" -gt 0 ] 2>/dev/null; then
  if [ $((EXPIRY - NOW_TS)) -lt $SEVEN_DAYS ]; then
    echo "Instagram token expiring soon — refreshing..." >&2
    REFRESH_RESP="$(curl -sS --max-time 15 \
      "https://graph.facebook.com/v19.0/oauth/access_token?grant_type=fb_exchange_token&client_id=${META_APP_ID}&client_secret=${META_APP_SECRET}&fb_exchange_token=${INSTAGRAM_ACCESS_TOKEN}" \
      2>/dev/null || echo '{}')"
    NEW_TOKEN="$(echo "$REFRESH_RESP" | jq -r '.access_token // empty')"
    NEW_EXPIRY_IN="$(echo "$REFRESH_RESP" | jq -r '.expires_in // 0')"
    if [ -n "$NEW_TOKEN" ]; then
      INSTAGRAM_ACCESS_TOKEN="$NEW_TOKEN"
      NEW_EXPIRY_TS=$(( NOW_TS + NEW_EXPIRY_IN ))
      sed -i "s|INSTAGRAM_ACCESS_TOKEN=.*|INSTAGRAM_ACCESS_TOKEN=$NEW_TOKEN|" "$HOME/.openclaw/.env" || true
      sed -i "s|INSTAGRAM_TOKEN_EXPIRY=.*|INSTAGRAM_TOKEN_EXPIRY=$NEW_EXPIRY_TS|" "$HOME/.openclaw/.env" || true
      echo "Token refreshed (expires $(date -u -d "@$NEW_EXPIRY_TS" +%Y-%m-%d 2>/dev/null || echo 'unknown'))" >&2
    else
      echo "WARNING: token refresh failed — proceeding with existing token" >&2
    fi
  fi
fi

BASE_URL="https://graph.facebook.com/v19.0/${INSTAGRAM_USER_ID}"

# --- Step 1: Create media container ---
if [ -n "$IMAGE_URL" ]; then
  # Image post
  CONTAINER_PAYLOAD="$(jq -n \
    --arg caption "$CONTENT" \
    --arg image_url "$IMAGE_URL" \
    --arg token "$INSTAGRAM_ACCESS_TOKEN" \
    '{caption: $caption, image_url: $image_url, access_token: $token}')"

  CONTAINER_RESP="$(curl -sS --max-time 30 \
    -X POST "${BASE_URL}/media" \
    -H "Content-Type: application/json" \
    -d "$CONTAINER_PAYLOAD" 2>/dev/null)"
else
  # Caption-only (reels/text not supported; requires image for feed posts)
  # Use a story or text post if no image — Instagram requires media for feed posts
  # Post as a reel placeholder using a blank approach isn't valid;
  # we require an image_url. Flag this case.
  echo "ERROR: Instagram feed posts require an image_url in the post JSON" >&2
  echo "Add \"image_url\": \"https://...\" to the post JSON or upload manually." >&2
  exit 1
fi

if echo "$CONTAINER_RESP" | jq -e '.error' > /dev/null 2>&1; then
  ERR="$(echo "$CONTAINER_RESP" | jq -r '.error.message // .error')"
  echo "ERROR: Instagram container creation failed: $ERR" >&2
  exit 1
fi

CREATION_ID="$(echo "$CONTAINER_RESP" | jq -r '.id // empty')"
if [ -z "$CREATION_ID" ]; then
  echo "ERROR: No creation_id returned from Instagram API" >&2
  echo "Response: $CONTAINER_RESP" >&2
  exit 1
fi

echo "Container created: $CREATION_ID" >&2

# --- Wait for container status to be FINISHED ---
MAX_WAIT=30
WAITED=0
while [ "$WAITED" -lt "$MAX_WAIT" ]; do
  STATUS_RESP="$(curl -sS --max-time 10 \
    "${BASE_URL}/media/${CREATION_ID}?fields=status_code&access_token=${INSTAGRAM_ACCESS_TOKEN}" \
    2>/dev/null || echo '{}')"
  STATUS_CODE="$(echo "$STATUS_RESP" | jq -r '.status_code // empty')"
  [ "$STATUS_CODE" = "FINISHED" ] && break
  [ "$STATUS_CODE" = "ERROR" ] && {
    echo "ERROR: Instagram media processing failed" >&2
    exit 1
  }
  sleep 2
  WAITED=$((WAITED + 2))
done

# --- Step 2: Publish the container ---
PUBLISH_RESP="$(curl -sS --max-time 30 \
  -X POST "${BASE_URL}/media_publish" \
  -H "Content-Type: application/json" \
  -d "$(jq -n \
    --arg id "$CREATION_ID" \
    --arg token "$INSTAGRAM_ACCESS_TOKEN" \
    '{creation_id: $id, access_token: $token}')" \
  2>/dev/null)"

if echo "$PUBLISH_RESP" | jq -e '.error' > /dev/null 2>&1; then
  ERR="$(echo "$PUBLISH_RESP" | jq -r '.error.message // .error')"
  echo "ERROR: Instagram publish failed: $ERR" >&2
  exit 1
fi

MEDIA_ID="$(echo "$PUBLISH_RESP" | jq -r '.id // empty')"
if [ -z "$MEDIA_ID" ]; then
  echo "ERROR: No media_id returned from publish" >&2
  echo "Response: $PUBLISH_RESP" >&2
  exit 1
fi

# Instagram Graph API doesn't return a direct permalink in the publish response
# Fetch it separately
PERMALINK_RESP="$(curl -sS --max-time 10 \
  "https://graph.facebook.com/v19.0/${MEDIA_ID}?fields=permalink&access_token=${INSTAGRAM_ACCESS_TOKEN}" \
  2>/dev/null || echo '{}')"
PERMALINK="$(echo "$PERMALINK_RESP" | jq -r '.permalink // empty')"

if [ -n "$PERMALINK" ]; then
  echo "$PERMALINK"
else
  echo "https://www.instagram.com/p/${MEDIA_ID}/"
fi
