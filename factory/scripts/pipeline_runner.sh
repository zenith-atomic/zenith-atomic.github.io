#!/usr/bin/env bash
set -euo pipefail

FACTORY="$HOME/.openclaw/workspace/factory"
SCRIPTS="$FACTORY/scripts"

# Resolve current week
WEEK="$(date -u +%Y-W%V)"
WEEK_DIR="$FACTORY/output/$WEEK"
STATE_FILE="$WEEK_DIR/pipeline.state"

# If no week folder, create it and start fresh
if [ ! -f "$STATE_FILE" ]; then
  mkdir -p "$WEEK_DIR"
  jq -n --arg week "$WEEK" --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{week:$week, created:$now, stages:{research:{status:"pending"},strategy:{status:"pending"},writing:{status:"pending"},visuals:{status:"pending"},publishing:{status:"pending"},analytics:{status:"pending"},evolution:{status:"pending"}}}' \
    > "$STATE_FILE"
fi

# Reconcile state with actual output files — prevents re-running stages that
# completed via standalone commands (/factory research, /factory strategy, etc.)
mark_done() {
  local stage="$1"
  local current
  current="$(jq -r ".stages.${stage}.status" "$STATE_FILE")"
  if [ "$current" != "done" ]; then
    local TMP
    TMP="$(mktemp)"
    jq --arg stage "$stage" --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
      '.stages[$stage] = {status:"done", completed:$now, reconciled:true}' \
      "$STATE_FILE" > "$TMP"
    mv "$TMP" "$STATE_FILE"
  fi
}

[ -f "$WEEK_DIR/research.md" ]             && mark_done "research"
[ -f "$WEEK_DIR/strategy.md" ]             && mark_done "strategy"
[ -f "$WEEK_DIR/drafts/all_drafts.md" ]    && mark_done "writing"
[ -f "$WEEK_DIR/visuals/all_visuals.md" ]  && mark_done "visuals"
[ -f "$WEEK_DIR/publishing_checklist.md" ] && mark_done "publishing"
[ -f "$WEEK_DIR/report.md" ]               && mark_done "analytics"

# Pipeline order
STAGES=("research" "strategy" "writing" "visuals" "publishing" "analytics" "evolution")
STAGE_SCRIPTS=(
  "$SCRIPTS/research_agent.sh"
  "$SCRIPTS/strategy_agent.sh"
  "$SCRIPTS/writer_agent.sh"
  "$SCRIPTS/creative_agent.sh"
  "$SCRIPTS/publisher_agent.sh"
  "$SCRIPTS/analytics_agent.sh"
  "$SCRIPTS/evolve_persona.sh"
)

# Find next pending stage and run it
for i in "${!STAGES[@]}"; do
  STAGE="${STAGES[$i]}"
  STATUS="$(jq -r ".stages.${STAGE}.status" "$STATE_FILE")"

  if [ "$STATUS" = "pending" ]; then
    echo "Running stage: $STAGE"
    SCRIPT="${STAGE_SCRIPTS[$i]}"

    if "$SCRIPT"; then
      echo "Stage $STAGE completed successfully."
      # After publishing stage, kick off the approval staging
      if [ "$STAGE" = "publishing" ] && [ -f "$SCRIPTS/stage_posts.sh" ]; then
        echo "Staging posts for approval..."
        "$SCRIPTS/stage_posts.sh" || echo "WARNING: stage_posts.sh failed — approval queue not created" >&2
      fi
    else
      echo "Stage $STAGE failed. Pipeline paused."
      exit 1
    fi
    exit 0
  fi
done

echo "All stages complete for $WEEK. Pipeline finished."
echo ""
"$SCRIPTS/status.sh"
