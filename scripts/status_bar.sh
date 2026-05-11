#!/usr/bin/env bash
set -euo pipefail

USAGE_TEXT="$(openclaw status --usage 2>/dev/null || true)"
FIVE_PCT="$(printf '%s\n' "$USAGE_TEXT" | sed -n 's/.*5h: \([0-9][0-9]*\)%.*/\1/p' | head -n1)"
WEEK_PCT="$(printf '%s\n' "$USAGE_TEXT" | sed -n 's/.*Week: \([0-9][0-9]*\)%.*/\1/p' | head -n1)"

bar() {
  pct="$1"
  [ -n "$pct" ] || pct=0
  filled=$((pct / 5))
  empty=$((20 - filled))
  out='['
  i=0
  while [ "$i" -lt "$filled" ]; do out="$out█"; i=$((i+1)); done
  i=0
  while [ "$i" -lt "$empty" ]; do out="$out░"; i=$((i+1)); done
  out="$out] ${pct}%"
  printf '%s' "$out"
}

[ -n "$FIVE_PCT" ] || FIVE_PCT=0
[ -n "$WEEK_PCT" ] || WEEK_PCT=0

printf 'Codex 5h: %s\n' "$(bar "$FIVE_PCT")"
printf 'Codex week: %s\n' "$(bar "$WEEK_PCT")"
