#!/usr/bin/env bash
set -euo pipefail

WORKDIR="/home/ai/.openclaw/workspace"
STATUS_BAR="$WORKDIR/scripts/status_bar.sh"

CMD="${1:-}"
shift || true

case "$CMD" in
  status)
    openclaw --no-color models status
    "$STATUS_BAR"
    ;;
  model)
    ALIAS="${1:-}"
    case "$ALIAS" in
      codex)      MODEL="openai-codex/gpt-5.4" ;;
      codex-mini) MODEL="openai-codex/gpt-5.4-mini" ;;
      nano)       MODEL="openai/gpt-5.4-nano" ;;
      gpt)        MODEL="openai/gpt-5.4" ;;
      gpt-mini)   MODEL="openai/gpt-5.4-mini" ;;
      *)
        printf 'unknown model alias: %s\nvalid: codex | codex-mini | nano | gpt | gpt-mini\n' "$ALIAS" >&2
        exit 1
        ;;
    esac
    openclaw models set "$MODEL"
    printf 'model set to %s\n' "$MODEL"
    ;;
  *)
    printf 'usage: router_dispatch.sh {status|model <alias>}\n' >&2
    exit 1
    ;;
esac
