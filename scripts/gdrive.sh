#!/usr/bin/env bash
# gdrive.sh — General-purpose Google Drive/Docs/Sheets CLI
#
# Usage:
#   gdrive.sh <command> [options]
#
# Commands:
#   create-doc    <title> [folder-id]          Create a Google Doc
#   create-sheet  <title> [folder-id]          Create a Google Sheet
#   create-folder <name>  [parent-folder-id]   Create a Drive folder
#   write-doc     <doc-id> <text>              Overwrite a Doc's body with text
#   append-doc    <doc-id> <text>              Append text to a Doc
#   read-doc      <doc-id>                     Print a Doc's plain text
#   sheet-append  <sheet-id> <tab> <json>      Append rows to a Sheet tab (json: [[v,v,...],...]  )
#   sheet-read    <sheet-id> <range>           Read a range (e.g. "Sheet1!A1:Z100")
#   sheet-write   <sheet-id> <range> <json>    Write values to a range
#   sheet-clear   <sheet-id> <range>           Clear a range
#   move          <file-id> <folder-id>        Move a file to a folder
#   rename        <file-id> <new-name>         Rename a file
#   delete        <file-id>                    Trash a file
#   share         <file-id> <email> [role]     Share with email (role: reader|writer|owner, default: writer)
#   share-public  <file-id> [role]             Make file publicly readable (role: reader|writer)
#   info          <file-id>                    Get file metadata (JSON)
#   list          [folder-id]                  List files (root if omitted)
#   find          <name>                       Search Drive by name
#   url           <file-id>                    Print the file's edit/view URL
#
# All commands print their primary result (ID, URL, or data) to stdout.
# Errors go to stderr.

set -euo pipefail

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Auth ──────────────────────────────────────────────────────────────────────
_token() {
  bash "$SCRIPTS_DIR/google_token.sh"
}

# ── Helpers ───────────────────────────────────────────────────────────────────
_drive_post() {
  local token="$1" endpoint="$2" body="$3"
  curl -sS --max-time 30 \
    -X POST "https://www.googleapis.com/drive/v3/${endpoint}" \
    -H "Authorization: Bearer $token" \
    -H "Content-Type: application/json" \
    -d "$body"
}

_drive_patch() {
  local token="$1" endpoint="$2" body="$3"
  curl -sS --max-time 30 \
    -X PATCH "https://www.googleapis.com/drive/v3/${endpoint}" \
    -H "Authorization: Bearer $token" \
    -H "Content-Type: application/json" \
    -d "$body"
}

_drive_get() {
  local token="$1" endpoint="$2"
  curl -sS --max-time 30 \
    "https://www.googleapis.com/drive/v3/${endpoint}" \
    -H "Authorization: Bearer $token"
}

_check_error() {
  local resp="$1" context="$2"
  if echo "$resp" | jq -e '.error' > /dev/null 2>&1; then
    echo "ERROR [$context]: $(echo "$resp" | jq -r '.error.message // .error')" >&2
    exit 1
  fi
}

_file_url() {
  local file_id="$1" mime="$2"
  case "$mime" in
    *spreadsheet*) echo "https://docs.google.com/spreadsheets/d/${file_id}/edit" ;;
    *document*)    echo "https://docs.google.com/document/d/${file_id}/edit" ;;
    *folder*)      echo "https://drive.google.com/drive/folders/${file_id}" ;;
    *)             echo "https://drive.google.com/file/d/${file_id}/view" ;;
  esac
}

# ── Commands ──────────────────────────────────────────────────────────────────
cmd_create_doc() {
  local title="${1:?Usage: gdrive.sh create-doc <title> [folder-id]}"
  local folder="${2:-}"
  local token; token="$(_token)"

  local body
  body="$(jq -n --arg t "$title" '{title: $t}')"
  local resp
  resp="$(curl -sS --max-time 30 \
    -X POST "https://docs.googleapis.com/v1/documents" \
    -H "Authorization: Bearer $token" \
    -H "Content-Type: application/json" \
    -d "$body")"
  _check_error "$resp" "create-doc"

  local doc_id; doc_id="$(echo "$resp" | jq -r '.documentId')"

  if [ -n "$folder" ]; then
    # Move into folder
    local current_parents
    current_parents="$(curl -sS --max-time 15 \
      "https://www.googleapis.com/drive/v3/files/${doc_id}?fields=parents" \
      -H "Authorization: Bearer $token" | jq -r '.parents | join(",")')"
    curl -sS --max-time 15 -X PATCH \
      "https://www.googleapis.com/drive/v3/files/${doc_id}?addParents=${folder}&removeParents=${current_parents}&fields=id" \
      -H "Authorization: Bearer $token" > /dev/null
  fi

  echo "$doc_id"
  echo "https://docs.google.com/document/d/${doc_id}/edit" >&2
}

cmd_create_sheet() {
  local title="${1:?Usage: gdrive.sh create-sheet <title> [folder-id]}"
  local folder="${2:-}"
  local token; token="$(_token)"

  local body; body="$(jq -n --arg t "$title" '{properties: {title: $t}}')"
  local resp
  resp="$(curl -sS --max-time 30 \
    -X POST "https://sheets.googleapis.com/v4/spreadsheets" \
    -H "Authorization: Bearer $token" \
    -H "Content-Type: application/json" \
    -d "$body")"
  _check_error "$resp" "create-sheet"

  local sheet_id; sheet_id="$(echo "$resp" | jq -r '.spreadsheetId')"

  if [ -n "$folder" ]; then
    local current_parents
    current_parents="$(curl -sS --max-time 15 \
      "https://www.googleapis.com/drive/v3/files/${sheet_id}?fields=parents" \
      -H "Authorization: Bearer $token" | jq -r '.parents | join(",")')"
    curl -sS --max-time 15 -X PATCH \
      "https://www.googleapis.com/drive/v3/files/${sheet_id}?addParents=${folder}&removeParents=${current_parents}&fields=id" \
      -H "Authorization: Bearer $token" > /dev/null
  fi

  echo "$sheet_id"
  echo "https://docs.google.com/spreadsheets/d/${sheet_id}/edit" >&2
}

cmd_create_folder() {
  local name="${1:?Usage: gdrive.sh create-folder <name> [parent-folder-id]}"
  local parent="${2:-}"
  local token; token="$(_token)"

  local body
  if [ -n "$parent" ]; then
    body="$(jq -n --arg n "$name" --arg p "$parent" \
      '{name: $n, mimeType: "application/vnd.google-apps.folder", parents: [$p]}')"
  else
    body="$(jq -n --arg n "$name" \
      '{name: $n, mimeType: "application/vnd.google-apps.folder"}')"
  fi

  local resp; resp="$(_drive_post "$token" "files?fields=id,name" "$body")"
  _check_error "$resp" "create-folder"

  local folder_id; folder_id="$(echo "$resp" | jq -r '.id')"
  echo "$folder_id"
  echo "https://drive.google.com/drive/folders/${folder_id}" >&2
}

cmd_write_doc() {
  local doc_id="${1:?Usage: gdrive.sh write-doc <doc-id> <text>}"
  local text="${2:?text required}"
  local token; token="$(_token)"

  # Get current end index to clear the doc first
  local meta
  meta="$(curl -sS --max-time 15 \
    "https://docs.googleapis.com/v1/documents/${doc_id}" \
    -H "Authorization: Bearer $token")"
  _check_error "$meta" "write-doc/get"

  local end_index; end_index="$(echo "$meta" | jq -r '.body.content[-1].endIndex // 2')"
  local requests="[]"

  # Delete existing content if doc has content (endIndex > 2 means non-empty)
  if [ "$end_index" -gt 2 ]; then
    local del_end=$(( end_index - 1 ))
    requests="$(jq -n --argjson e "$del_end" \
      '[{deleteContentRange: {range: {startIndex: 1, endIndex: $e}}}]')"
  fi

  # Insert new text
  requests="$(echo "$requests" | jq \
    --arg t "$text" \
    '. + [{insertText: {location: {index: 1}, text: $t}}]')"

  local resp
  resp="$(curl -sS --max-time 30 \
    -X POST "https://docs.googleapis.com/v1/documents/${doc_id}:batchUpdate" \
    -H "Authorization: Bearer $token" \
    -H "Content-Type: application/json" \
    -d "{\"requests\": $requests}")"
  _check_error "$resp" "write-doc/update"

  echo "$doc_id"
}

cmd_append_doc() {
  local doc_id="${1:?Usage: gdrive.sh append-doc <doc-id> <text>}"
  local text="${2:?text required}"
  local token; token="$(_token)"

  # Get end index
  local meta
  meta="$(curl -sS --max-time 15 \
    "https://docs.googleapis.com/v1/documents/${doc_id}" \
    -H "Authorization: Bearer $token")"
  _check_error "$meta" "append-doc/get"

  local end_index; end_index="$(echo "$meta" | jq -r '.body.content[-1].endIndex // 1')"
  local insert_index=$(( end_index - 1 ))
  [ "$insert_index" -lt 1 ] && insert_index=1

  local body
  body="$(jq -n --arg t "$text" --argjson i "$insert_index" \
    '{requests: [{insertText: {location: {index: $i}, text: $t}}]}')"

  local resp
  resp="$(curl -sS --max-time 30 \
    -X POST "https://docs.googleapis.com/v1/documents/${doc_id}:batchUpdate" \
    -H "Authorization: Bearer $token" \
    -H "Content-Type: application/json" \
    -d "$body")"
  _check_error "$resp" "append-doc"

  echo "$doc_id"
}

cmd_read_doc() {
  local doc_id="${1:?Usage: gdrive.sh read-doc <doc-id>}"
  local token; token="$(_token)"

  local resp
  resp="$(curl -sS --max-time 30 \
    "https://docs.googleapis.com/v1/documents/${doc_id}" \
    -H "Authorization: Bearer $token")"
  _check_error "$resp" "read-doc"

  # Extract plain text from content elements
  echo "$resp" | jq -r '
    [.body.content[]
      | .paragraph.elements[]?
      | .textRun.content // empty]
    | join("")'
}

cmd_sheet_append() {
  local sheet_id="${1:?Usage: gdrive.sh sheet-append <sheet-id> <tab> <json>}"
  local tab="${2:?tab required}"
  local json="${3:?json rows required}"
  local token; token="$(_token)"

  local body; body="$(jq -n --argjson v "$json" '{values: $v}')"
  local resp
  resp="$(curl -sS --max-time 30 \
    -X POST "https://sheets.googleapis.com/v4/spreadsheets/${sheet_id}/values/$(python3 -c "import urllib.parse; print(urllib.parse.quote('${tab}'))" 2>/dev/null || echo "${tab}"):append?valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS" \
    -H "Authorization: Bearer $token" \
    -H "Content-Type: application/json" \
    -d "$body")"
  _check_error "$resp" "sheet-append"

  echo "$resp" | jq -r '.updates.updatedRange // "ok"'
}

cmd_sheet_read() {
  local sheet_id="${1:?Usage: gdrive.sh sheet-read <sheet-id> <range>}"
  local range="${2:?range required}"
  local token; token="$(_token)"

  local encoded_range; encoded_range="$(python3 -c "import urllib.parse; print(urllib.parse.quote('${range}'))" 2>/dev/null || echo "$range")"
  local resp
  resp="$(curl -sS --max-time 30 \
    "https://sheets.googleapis.com/v4/spreadsheets/${sheet_id}/values/${encoded_range}" \
    -H "Authorization: Bearer $token")"
  _check_error "$resp" "sheet-read"

  echo "$resp" | jq '.values // []'
}

cmd_sheet_write() {
  local sheet_id="${1:?Usage: gdrive.sh sheet-write <sheet-id> <range> <json>}"
  local range="${2:?range required}"
  local json="${3:?json values required}"
  local token; token="$(_token)"

  local encoded_range; encoded_range="$(python3 -c "import urllib.parse; print(urllib.parse.quote('${range}'))" 2>/dev/null || echo "$range")"
  local body; body="$(jq -n --argjson v "$json" --arg r "$range" '{range: $r, values: $v}')"
  local resp
  resp="$(curl -sS --max-time 30 \
    -X PUT "https://sheets.googleapis.com/v4/spreadsheets/${sheet_id}/values/${encoded_range}?valueInputOption=USER_ENTERED" \
    -H "Authorization: Bearer $token" \
    -H "Content-Type: application/json" \
    -d "$body")"
  _check_error "$resp" "sheet-write"

  echo "$resp" | jq -r '.updatedRange // "ok"'
}

cmd_sheet_clear() {
  local sheet_id="${1:?Usage: gdrive.sh sheet-clear <sheet-id> <range>}"
  local range="${2:?range required}"
  local token; token="$(_token)"

  local encoded_range; encoded_range="$(python3 -c "import urllib.parse; print(urllib.parse.quote('${range}'))" 2>/dev/null || echo "$range")"
  local resp
  resp="$(curl -sS --max-time 30 \
    -X POST "https://sheets.googleapis.com/v4/spreadsheets/${sheet_id}/values/${encoded_range}:clear" \
    -H "Authorization: Bearer $token" \
    -H "Content-Type: application/json" \
    -d '{}')"
  _check_error "$resp" "sheet-clear"

  echo "$resp" | jq -r '.clearedRange // "ok"'
}

cmd_move() {
  local file_id="${1:?Usage: gdrive.sh move <file-id> <folder-id>}"
  local folder_id="${2:?folder-id required}"
  local token; token="$(_token)"

  local current_parents
  current_parents="$(curl -sS --max-time 15 \
    "https://www.googleapis.com/drive/v3/files/${file_id}?fields=parents" \
    -H "Authorization: Bearer $token" | jq -r '.parents | join(",")')"

  local resp
  resp="$(curl -sS --max-time 15 -X PATCH \
    "https://www.googleapis.com/drive/v3/files/${file_id}?addParents=${folder_id}&removeParents=${current_parents}&fields=id,name" \
    -H "Authorization: Bearer $token" \
    -H "Content-Type: application/json" \
    -d '{}')"
  _check_error "$resp" "move"
  echo "$file_id"
}

cmd_rename() {
  local file_id="${1:?Usage: gdrive.sh rename <file-id> <new-name>}"
  local new_name="${2:?new-name required}"
  local token; token="$(_token)"

  local resp
  resp="$(_drive_patch "$token" "files/${file_id}?fields=id,name" \
    "$(jq -n --arg n "$new_name" '{name: $n}')")"
  _check_error "$resp" "rename"
  echo "$file_id"
}

cmd_delete() {
  local file_id="${1:?Usage: gdrive.sh delete <file-id>}"
  local token; token="$(_token)"

  local resp
  resp="$(_drive_patch "$token" "files/${file_id}?fields=id" '{"trashed": true}')"
  _check_error "$resp" "delete"
  echo "trashed: $file_id"
}

cmd_share() {
  local file_id="${1:?Usage: gdrive.sh share <file-id> <email> [role]}"
  local email="${2:?email required}"
  local role="${3:-writer}"
  local token; token="$(_token)"

  local body; body="$(jq -n --arg r "$role" --arg e "$email" \
    '{role: $r, type: "user", emailAddress: $e}')"
  local resp
  resp="$(_drive_post "$token" "files/${file_id}/permissions?fields=id" "$body")"
  _check_error "$resp" "share"
  echo "shared $file_id with $email as $role"
}

cmd_share_public() {
  local file_id="${1:?Usage: gdrive.sh share-public <file-id> [role]}"
  local role="${2:-reader}"
  local token; token="$(_token)"

  local body; body="$(jq -n --arg r "$role" '{role: $r, type: "anyone"}')"
  local resp
  resp="$(_drive_post "$token" "files/${file_id}/permissions?fields=id" "$body")"
  _check_error "$resp" "share-public"
  echo "public $role: $file_id"
}

cmd_info() {
  local file_id="${1:?Usage: gdrive.sh info <file-id>}"
  local token; token="$(_token)"

  local resp
  resp="$(_drive_get "$token" "files/${file_id}?fields=id,name,mimeType,createdTime,modifiedTime,size,parents,webViewLink")"
  _check_error "$resp" "info"
  echo "$resp" | jq .
}

cmd_list() {
  local folder="${1:-root}"
  local token; token="$(_token)"

  local query="'${folder}' in parents and trashed=false"
  local encoded_q; encoded_q="$(python3 -c "import urllib.parse; print(urllib.parse.quote('${query}'))" 2>/dev/null || echo "$query")"
  local resp
  resp="$(_drive_get "$token" "files?q=${encoded_q}&fields=files(id,name,mimeType,modifiedTime)&orderBy=modifiedTime+desc&pageSize=50")"
  _check_error "$resp" "list"
  echo "$resp" | jq -r '.files[] | [.id, .mimeType, .name] | @tsv'
}

cmd_find() {
  local name="${1:?Usage: gdrive.sh find <name>}"
  local token; token="$(_token)"

  local query="name contains '${name}' and trashed=false"
  local encoded_q; encoded_q="$(python3 -c "import urllib.parse; print(urllib.parse.quote(\"${query}\"))" 2>/dev/null || echo "$query")"
  local resp
  resp="$(_drive_get "$token" "files?q=${encoded_q}&fields=files(id,name,mimeType,modifiedTime)&orderBy=modifiedTime+desc&pageSize=20")"
  _check_error "$resp" "find"
  echo "$resp" | jq -r '.files[] | [.id, .mimeType, .name] | @tsv'
}

cmd_url() {
  local file_id="${1:?Usage: gdrive.sh url <file-id>}"
  local token; token="$(_token)"

  local resp
  resp="$(_drive_get "$token" "files/${file_id}?fields=id,mimeType,webViewLink")"
  _check_error "$resp" "url"
  echo "$resp" | jq -r '.webViewLink'
}

# ── Dispatch ──────────────────────────────────────────────────────────────────
CMD="${1:-help}"
shift || true

case "$CMD" in
  create-doc)    cmd_create_doc "$@" ;;
  create-sheet)  cmd_create_sheet "$@" ;;
  create-folder) cmd_create_folder "$@" ;;
  write-doc)     cmd_write_doc "$@" ;;
  append-doc)    cmd_append_doc "$@" ;;
  read-doc)      cmd_read_doc "$@" ;;
  sheet-append)  cmd_sheet_append "$@" ;;
  sheet-read)    cmd_sheet_read "$@" ;;
  sheet-write)   cmd_sheet_write "$@" ;;
  sheet-clear)   cmd_sheet_clear "$@" ;;
  move)          cmd_move "$@" ;;
  rename)        cmd_rename "$@" ;;
  delete)        cmd_delete "$@" ;;
  share)         cmd_share "$@" ;;
  share-public)  cmd_share_public "$@" ;;
  info)          cmd_info "$@" ;;
  list)          cmd_list "$@" ;;
  find)          cmd_find "$@" ;;
  url)           cmd_url "$@" ;;
  help|--help|-h)
    sed -n '/^# Usage:/,/^$/p' "$0"
    exit 0
    ;;
  *)
    echo "Unknown command: $CMD. Run: gdrive.sh help" >&2
    exit 1
    ;;
esac
