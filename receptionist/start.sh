#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="/home/ai/.openclaw/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: .env not found at $ENV_FILE" >&2
  exit 1
fi

set -a; source "$ENV_FILE"; set +a

if [[ -z "${ELEVENLABS_AGENT_ID:-}" ]]; then
  echo "ERROR: ELEVENLABS_AGENT_ID is not set in $ENV_FILE"
  echo "  → Create an agent at https://elevenlabs.io/app/conversational-ai"
  echo "  → Copy the Agent ID and add it to .env"
  exit 1
fi

cd "$SCRIPT_DIR"
exec bun run src/server.ts
