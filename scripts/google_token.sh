#!/usr/bin/env bash
# google_token.sh — Get a fresh Google access token using the stored refresh token
#
# Usage:
#   ACCESS_TOKEN="$(bash "$HOME/.openclaw/workspace/scripts/google_token.sh")"
#
# Requires in environment (or sourced from ~/.openclaw/.env):
#   GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN
#
# Outputs the access token to stdout. Exits non-zero on failure.

set -euo pipefail

if [ -f "$HOME/.openclaw/.env" ]; then
  set +u; source "$HOME/.openclaw/.env"; set -u
fi

: "${GOOGLE_CLIENT_ID:?GOOGLE_CLIENT_ID not set}"
: "${GOOGLE_CLIENT_SECRET:?GOOGLE_CLIENT_SECRET not set}"
: "${GOOGLE_REFRESH_TOKEN:?GOOGLE_REFRESH_TOKEN not set}"

RESP="$(curl -sS --max-time 15 \
  "https://oauth2.googleapis.com/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=${GOOGLE_CLIENT_ID}&client_secret=${GOOGLE_CLIENT_SECRET}&refresh_token=${GOOGLE_REFRESH_TOKEN}&grant_type=refresh_token")"

TOKEN="$(echo "$RESP" | jq -r '.access_token // empty')"

if [ -z "$TOKEN" ]; then
  echo "ERROR: Google token refresh failed: $(echo "$RESP" | jq -r '.error_description // .error // .')" >&2
  exit 1
fi

echo "$TOKEN"
