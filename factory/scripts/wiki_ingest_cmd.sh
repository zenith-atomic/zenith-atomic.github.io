#!/usr/bin/env bash
#
# wiki_ingest_cmd.sh — Ingest a URL or PDF into the wiki from Telegram.
#
# Usage:
#   wiki_ingest_cmd.sh <url>                     # Fetch URL and ingest
#   wiki_ingest_cmd.sh <local-pdf-path>          # Convert local PDF and ingest
#   wiki_ingest_cmd.sh <file-id> --telegram      # Download PDF from Telegram and ingest
#
# Output is plain text suitable for sending back to Telegram.
#
set -euo pipefail

WORKSPACE="$HOME/.openclaw/workspace"
WIKI_SCRIPTS="$WORKSPACE/wiki/scripts"
TMP_DIR="/tmp/wiki_ingest_$$"

# ── Load credentials ──────────────────────────────────────────────────────────
if [ -f "$HOME/.openclaw/.env" ]; then
  # shellcheck disable=SC1091
  set +u; source "$HOME/.openclaw/.env"; set -u
fi

BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-$(jq -r '.channels.telegram.botToken' \
  "$HOME/.openclaw/openclaw.json" 2>/dev/null || echo "")}"

# ── Args ──────────────────────────────────────────────────────────────────────
ARG="${1:-}"
MODE="${2:-}"

if [ -z "$ARG" ]; then
  cat <<'USAGE'
Usage:
  /factory ingest <url>            — fetch a web page into the wiki
  /factory ingest <pdf-path>       — ingest a local PDF file

To ingest a PDF directly: send the PDF as a document to this bot.
USAGE
  exit 1
fi

# ── Cleanup on exit ───────────────────────────────────────────────────────────
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

# ── Helper: run a wiki script and capture a clean summary ────────────────────
run_wiki_script() {
  local script="$1"
  shift
  # Run and capture output; on error print stderr too
  local out
  out="$("$script" "$@" 2>&1)" || {
    echo "ERROR during ingestion:"
    echo "$out" | tail -20
    exit 1
  }
  echo "$out"
}

# ─────────────────────────────────────────────────────────────────────────────
# MODE: --telegram  →  download from Telegram using file_id, then ingest PDF
# ─────────────────────────────────────────────────────────────────────────────
if [ "$MODE" = "--telegram" ]; then
  FILE_ID="$ARG"

  if [ -z "$BOT_TOKEN" ]; then
    echo "ERROR: TELEGRAM_BOT_TOKEN not configured."
    exit 1
  fi

  echo "Downloading document from Telegram..."
  mkdir -p "$TMP_DIR"

  # Get the file path on Telegram's CDN
  FILE_INFO="$(curl -sS --max-time 15 \
    "https://api.telegram.org/bot${BOT_TOKEN}/getFile?file_id=${FILE_ID}")"
  FILE_PATH="$(echo "$FILE_INFO" | jq -r '.result.file_path // empty' 2>/dev/null)"

  if [ -z "$FILE_PATH" ]; then
    echo "ERROR: Could not retrieve file from Telegram."
    echo "The file_id may have expired — Telegram file_ids are valid for ~24 hours."
    exit 1
  fi

  # Detect extension
  EXT="${FILE_PATH##*.}"
  FILENAME="$(basename "$FILE_PATH")"
  LOCAL_PATH="$TMP_DIR/$FILENAME"

  curl -sS --max-time 60 \
    "https://api.telegram.org/file/bot${BOT_TOKEN}/${FILE_PATH}" \
    -o "$LOCAL_PATH"

  if [ ! -s "$LOCAL_PATH" ]; then
    echo "ERROR: Downloaded file is empty."
    exit 1
  fi

  SIZE="$(wc -c < "$LOCAL_PATH")"
  echo "Downloaded: $FILENAME ($(( SIZE / 1024 )) KB)"

  # Only PDF is supported right now
  if [[ "${EXT,,}" == "pdf" ]]; then
    echo ""
    run_wiki_script "$WIKI_SCRIPTS/wiki_pdf.sh" "$LOCAL_PATH"
  else
    echo "ERROR: Only PDF files are supported for ingestion (got .${EXT})."
    echo "Supported: .pdf"
    exit 1
  fi

  exit 0
fi

# ─────────────────────────────────────────────────────────────────────────────
# AUTO-DETECT: URL or local file
# ─────────────────────────────────────────────────────────────────────────────
if [[ "$ARG" =~ ^https?:// ]]; then
  # ── URL ──────────────────────────────────────────────────────────────────
  # YouTube: detect by domain or youtu.be shortlink
  if [[ "$ARG" =~ (youtube\.com|youtu\.be) ]]; then
    echo "Ingesting YouTube video: $ARG"
    echo ""
    run_wiki_script "$WIKI_SCRIPTS/wiki_youtube.sh" "$ARG"
  else
    echo "Ingesting URL: $ARG"
    echo ""
    run_wiki_script "$WIKI_SCRIPTS/wiki_fetch.sh" "$ARG"
  fi

elif [[ -f "$ARG" ]]; then
  # ── Local file ────────────────────────────────────────────────────────────
  EXT="${ARG##*.}"
  if [[ "${EXT,,}" == "pdf" ]]; then
    echo "Ingesting PDF: $ARG"
    echo ""
    run_wiki_script "$WIKI_SCRIPTS/wiki_pdf.sh" "$ARG"
  else
    echo "ERROR: Unsupported file type (.${EXT}). Only .pdf is supported."
    exit 1
  fi

else
  echo "ERROR: '$ARG' is not a valid URL or file path."
  echo ""
  echo "Usage:"
  echo "  /factory ingest <url>        — ingest a web page"
  echo "  /factory ingest <pdf-path>   — ingest a local PDF"
  echo ""
  echo "To ingest a PDF from Telegram: send the file as a document to this bot."
  exit 1
fi
