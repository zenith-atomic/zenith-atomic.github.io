#!/usr/bin/env bash
# Post to LinkedIn Company Page via UGC Posts API
# Requires: LINKEDIN_ACCESS_TOKEN, LINKEDIN_ORG_ID
set -euo pipefail

if [ "${1:-}" = "" ]; then
  echo "Usage: post_linkedin.sh <post-json-file>" >&2
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

: "${LINKEDIN_ACCESS_TOKEN:?LINKEDIN_ACCESS_TOKEN not set}"
: "${LINKEDIN_ORG_ID:?LINKEDIN_ORG_ID not set}"

# Optional image asset (LinkedIn requires a multi-step upload for images)
IMAGE_URL="$(jq -r '.image_url // ""' "$POST_FILE")"

# --- Build UGC Post payload ---
# For text-only posts:
if [ -z "$IMAGE_URL" ]; then
  PAYLOAD="$(jq -n \
    --arg org "urn:li:organization:${LINKEDIN_ORG_ID}" \
    --arg text "$CONTENT" \
    '{
      author: $org,
      lifecycleState: "PUBLISHED",
      specificContent: {
        "com.linkedin.ugc.ShareContent": {
          shareCommentary: {text: $text},
          shareMediaCategory: "NONE"
        }
      },
      visibility: {
        "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
      }
    }')"
else
  # Image post: LinkedIn requires registering an upload first, then attaching the asset.
  # Step 1: Register upload
  REGISTER_PAYLOAD="$(jq -n \
    --arg org "urn:li:organization:${LINKEDIN_ORG_ID}" \
    '{
      registerUploadRequest: {
        recipes: ["urn:li:digitalmediaRecipe:feedshare-image"],
        owner: $org,
        serviceRelationships: [{
          relationshipType: "OWNER",
          identifier: "urn:li:userGeneratedContent"
        }]
      }
    }')"

  REGISTER_RESP="$(curl -sS --max-time 30 \
    -X POST "https://api.linkedin.com/v2/assets?action=registerUpload" \
    -H "Authorization: Bearer $LINKEDIN_ACCESS_TOKEN" \
    -H "Content-Type: application/json" \
    -d "$REGISTER_PAYLOAD" 2>/dev/null)"

  if echo "$REGISTER_RESP" | jq -e '.serviceErrorCode' > /dev/null 2>&1; then
    ERR="$(echo "$REGISTER_RESP" | jq -r '.message // .')"
    echo "ERROR: LinkedIn upload registration failed: $ERR" >&2
    exit 1
  fi

  UPLOAD_URL="$(echo "$REGISTER_RESP" | jq -r '.value.uploadMechanism["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"].uploadUrl // empty')"
  ASSET_URN="$(echo "$REGISTER_RESP" | jq -r '.value.asset // empty')"

  if [ -z "$UPLOAD_URL" ] || [ -z "$ASSET_URN" ]; then
    echo "ERROR: Could not get upload URL or asset URN from LinkedIn" >&2
    exit 1
  fi

  # Step 2: Download image and upload to LinkedIn
  TMP_IMG="$(mktemp --suffix=.jpg)"
  curl -sS --max-time 30 -L "$IMAGE_URL" -o "$TMP_IMG" 2>/dev/null
  curl -sS --max-time 60 \
    -X PUT "$UPLOAD_URL" \
    -H "Authorization: Bearer $LINKEDIN_ACCESS_TOKEN" \
    --data-binary "@$TMP_IMG" > /dev/null 2>&1
  rm -f "$TMP_IMG"

  # Step 3: Build payload with image asset
  PAYLOAD="$(jq -n \
    --arg org "urn:li:organization:${LINKEDIN_ORG_ID}" \
    --arg text "$CONTENT" \
    --arg asset "$ASSET_URN" \
    '{
      author: $org,
      lifecycleState: "PUBLISHED",
      specificContent: {
        "com.linkedin.ugc.ShareContent": {
          shareCommentary: {text: $text},
          shareMediaCategory: "IMAGE",
          media: [{
            status: "READY",
            media: $asset
          }]
        }
      },
      visibility: {
        "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
      }
    }')"
fi

# --- POST to UGC Posts API ---
RESP="$(curl -sS --max-time 30 \
  -X POST "https://api.linkedin.com/v2/ugcPosts" \
  -H "Authorization: Bearer $LINKEDIN_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-Restli-Protocol-Version: 2.0.0" \
  -d "$PAYLOAD" 2>/dev/null)"

if echo "$RESP" | jq -e '.serviceErrorCode' > /dev/null 2>&1; then
  ERR="$(echo "$RESP" | jq -r '.message // .')"
  echo "ERROR: LinkedIn post failed: $ERR" >&2
  exit 1
fi

# LinkedIn returns the post URN in the X-RestLi-Id header or in the id field
POST_URN="$(echo "$RESP" | jq -r '.id // empty')"
if [ -z "$POST_URN" ]; then
  echo "ERROR: No post ID returned from LinkedIn" >&2
  echo "Response: $RESP" >&2
  exit 1
fi

# Convert URN to URL: urn:li:ugcPost:1234567890 → numeric ID
POST_ID="$(echo "$POST_URN" | grep -oE '[0-9]+$')"
echo "https://www.linkedin.com/feed/update/${POST_URN}/"
