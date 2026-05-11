#!/usr/bin/env bash
# health_monitor.sh — OpenClaw service health check
# Alerts only on failures. Safe for cron.
# Usage: ./health_monitor.sh [--quiet]

set -Eeuo pipefail

QUIET_MODE="${1:-}"
LOG_PREFIX="[health_monitor]"
WORKSPACE_DIR="/home/ai/.openclaw/workspace"
CRON_LOG_DIR="$WORKSPACE_DIR/logs/cron"
NOW_UTC="$(date -u '+%Y-%m-%d %H:%M UTC')"
FAILED=0
ISSUES=()

log() { echo "$(date -u '+%Y-%m-%d %H:%M:%S') $LOG_PREFIX $1"; }

have() { command -v "$1" >/dev/null 2>&1; }

record_issue() {
  local component="$1"
  local detail="$2"
  ISSUES+=("- ${component}: ${detail}")
  FAILED=1
  log "FAIL $component: $detail"
}

send_alert() {
  local body="$1"
  if [ "$QUIET_MODE" = "--quiet" ]; then
    return 0
  fi

  if [ -z "${TELEGRAM_BOT_TOKEN:-}" ]; then
    log "TELEGRAM_BOT_TOKEN not set, skipping Telegram alert"
    return 0
  fi

  local chat_id="${OPENCLAW_HEALTH_CHAT_ID:-5492388075}"

  curl -fsS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${chat_id}" \
    --data-urlencode "text=${body}" \
    >/dev/null
}

check_http() {
  local name="$1"
  local url="$2"
  if curl -fsS --max-time 4 "$url" >/dev/null 2>&1; then
    log "$name OK"
  else
    record_issue "$name" "HTTP probe failed for $url"
  fi
}

check_process() {
  local name="$1"
  local pattern="$2"
  if pgrep -f "$pattern" >/dev/null 2>&1; then
    log "$name OK"
  else
    record_issue "$name" "process not running (pattern: $pattern)"
  fi
}

ensure_process() {
  local name="$1"
  local pattern="$2"
  local start_cmd="$3"
  if pgrep -f "$pattern" >/dev/null 2>&1; then
    log "$name OK"
  else
    log "$name not running — starting"
    eval "$start_cmd" >> "/tmp/${name}.log" 2>&1 &
    sleep 1
    if pgrep -f "$pattern" >/dev/null 2>&1; then
      log "$name started OK"
    else
      record_issue "$name" "failed to start (cmd: $start_cmd)"
    fi
  fi
}

check_disk() {
  local usage
  usage="$(df / | awk 'NR==2 {gsub(/%/, "", $5); print $5}')"
  if [ "${usage}" -ge 95 ]; then
    record_issue "disk" "root filesystem at ${usage}%"
  elif [ "${usage}" -ge 85 ]; then
    log "disk warning ${usage}%"
  else
    log "disk OK ${usage}%"
  fi
}

check_recent_cron_failures() {
  if [ ! -d "$CRON_LOG_DIR" ]; then
    log "cron log dir missing, skipping"
    return 0
  fi

  local failed_logs
  failed_logs="$(find "$CRON_LOG_DIR" -maxdepth 1 -type f -name '*.log' -mmin -20 -print0 | xargs -0 -r rg -l 'FAILED|ERROR' 2>/dev/null || true)"
  if [ -n "$failed_logs" ]; then
    record_issue "cron" "recent failures detected in $(echo "$failed_logs" | tr '\n' ' ' | sed 's/ $//')"
  else
    log "cron logs OK"
  fi
}

main() {
  log "starting health check"

  check_process gateway-process 'openclaw-gateway'
  check_http gateway http://127.0.0.1:18789/

  if pgrep -f 'ollama' >/dev/null 2>&1 || curl -fsS --max-time 2 http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
    check_http ollama http://127.0.0.1:11434/api/version
  else
    log 'ollama not running, skipping'
  fi

  check_process steel-browser 'steel-mcp-server/dist/index.js'
  ensure_process steel-cdp-proxy 'steel-cdp-proxy.js' \
    'nohup node /home/ai/.openclaw/workspace/scripts/steel-cdp-proxy.js'
  check_process google-drive-mcp 'google-mcp-server/index.js'
  check_process gbrain '/home/ai/gbrain/bin/gbrain serve'
  check_disk
  check_recent_cron_failures

  if [ "$FAILED" -eq 1 ]; then
    local message
    message=$(cat <<EOF
🔥 OpenClaw health alert
Time: ${NOW_UTC}

$(printf '%s
' "${ISSUES[@]}")
EOF
)
    send_alert "$message" || log "failed to send Telegram alert"
    log "health check failed"
    exit 1
  fi

  log "all checks passed"
}

main "$@"
