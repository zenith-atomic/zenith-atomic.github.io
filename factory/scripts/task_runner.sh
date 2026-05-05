#!/usr/bin/env bash
# Usage: task_runner.sh "<goal>" [project_id]
# Calls the orchestrator to plan, then executes the plan step by step.
set -euo pipefail

FACTORY="$HOME/.openclaw/workspace/factory"
SCRIPTS="$FACTORY/scripts"
PROJECTS_JSON="$FACTORY/projects.json"

TASK_GOAL="${1:-}"
PROJECT_ID="${2:-}"

if [ -z "$TASK_GOAL" ]; then
  echo "Usage: task_runner.sh \"<goal>\" [project_id]" >&2
  exit 1
fi

# --- helpers (defined early so they're available for all call sites) ---
function _fail_task() {
  local id="$1" logfile="$2" reason="$3"
  local tmp
  tmp="$(mktemp)"
  grep -v "\"id\":\"$id\"" "$logfile" > "$tmp" || true
  grep "\"id\":\"$id\"" "$logfile" \
    | jq --arg r "$reason" --arg t "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
         '.status = "failed" | .failed = $t | .error = $r' >> "$tmp" || true
  mv "$tmp" "$logfile"
}

function _complete_task() {
  local id="$1" logfile="$2"
  local tmp
  tmp="$(mktemp)"
  grep -v "\"id\":\"$id\"" "$logfile" > "$tmp" || true
  grep "\"id\":\"$id\"" "$logfile" \
    | jq --arg t "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
         '.status = "done" | .completed = $t' >> "$tmp" || true
  mv "$tmp" "$logfile"
}

# Resolve project — default if not specified
if [ -z "$PROJECT_ID" ]; then
  PROJECT_ID="$(jq -r '.default' "$PROJECTS_JSON")"
fi

PROJECT="$(jq -e --arg id "$PROJECT_ID" '.projects[] | select(.id == $id)' "$PROJECTS_JSON" 2>/dev/null)" || {
  echo "ERROR: Project '$PROJECT_ID' not found. Run: /factory project new <id> <name>" >&2
  exit 1
}

PROJECT_NAME="$(echo "$PROJECT" | jq -r '.name')"
FACTORY_CONFIG="$(echo "$PROJECT" | jq -r '.config')"
FACTORY_OUTPUT="$(echo "$PROJECT" | jq -r '.output')"
FACTORY_DIRECTIVES="$(echo "$PROJECT" | jq -r '.directives')"
FACTORY_ANALYTICS="$(echo "$PROJECT" | jq -r '.analytics')"
FACTORY_INBOX="$(echo "$PROJECT" | jq -r '.inbox')"
TASKS_DIR="$FACTORY/tasks/$PROJECT_ID"

mkdir -p "$TASKS_DIR"

# Generate task ID
TASK_ID="task-$(date -u +%Y%m%dT%H%M%S)"
TASK_LOG="$TASKS_DIR/tasks.jsonl"

echo "[$(date -u +%H:%M:%SZ)] Task $TASK_ID starting for project '$PROJECT_NAME'"
echo "[$(date -u +%H:%M:%SZ)] Goal: $TASK_GOAL"

# Write initial task record
TASK_RECORD="$(jq -n \
  --arg id "$TASK_ID" \
  --arg project "$PROJECT_ID" \
  --arg goal "$TASK_GOAL" \
  --arg created "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '{id:$id, project:$project, goal:$goal, status:"running", created:$created, plan:[], outputs:[]}')"
echo "$TASK_RECORD" >> "$TASK_LOG"

# Build project context summary for orchestrator
PERSONA_SUMMARY=""
if [ -f "$FACTORY_CONFIG/persona.yml" ]; then
  PERSONA_SUMMARY="$(head -5 "$FACTORY_CONFIG/persona.yml")"
fi

ORCHESTRATOR_MSG="## Task
$TASK_GOAL

## Project
id: $PROJECT_ID
name: $PROJECT_NAME

## Persona (summary)
$PERSONA_SUMMARY

Decompose this task into a factory agent execution plan. Return only JSON."

# Call orchestrator
echo "[$(date -u +%H:%M:%SZ)] Calling orchestrator to plan..."
TMP_ORCH="/tmp/factory_orchestrator_$TASK_ID.txt"
trap 'rm -f "$TMP_ORCH"' EXIT

openclaw agent --agent factory-orchestrator --local \
  --message "$ORCHESTRATOR_MSG" --timeout 60 --json \
  >/dev/null 2>"$TMP_ORCH"
ORCH_EXIT=$?
ORCH_JSON="$(sed -n '/^{/,$p' "$TMP_ORCH" | head -1)"

if [ $ORCH_EXIT -ne 0 ] || [ -z "$ORCH_JSON" ]; then
  echo "ERROR: orchestrator failed (exit $ORCH_EXIT)" >&2
  tail -3 "$TMP_ORCH" >&2
  _fail_task "$TASK_ID" "$TASK_LOG" "orchestrator failed"
  exit 1
fi

PLAN_TEXT="$(echo "$ORCH_JSON" | jq -r '.payloads[0].text // empty')"
if [ -z "$PLAN_TEXT" ]; then
  echo "ERROR: orchestrator returned empty response" >&2
  _fail_task "$TASK_ID" "$TASK_LOG" "empty orchestrator response"
  exit 1
fi

# Parse plan JSON (strip markdown fences if present)
PLAN_JSON="$(echo "$PLAN_TEXT" | sed 's/^```json//;s/^```//' | sed '/^```/d')"

# Validate it has a plan array
if ! echo "$PLAN_JSON" | jq -e '.plan' >/dev/null 2>&1; then
  # Check for no-agent message
  MSG="$(echo "$PLAN_JSON" | jq -r '.message // empty' 2>/dev/null || true)"
  if [ -n "$MSG" ]; then
    echo "Orchestrator: $MSG"
    _complete_task "$TASK_ID" "$TASK_LOG"
    exit 0
  fi
  echo "ERROR: orchestrator returned invalid plan: $PLAN_JSON" >&2
  _fail_task "$TASK_ID" "$TASK_LOG" "invalid plan JSON"
  exit 1
fi

STEPS="$(echo "$PLAN_JSON" | jq -c '.plan[]')"
STEP_COUNT="$(echo "$PLAN_JSON" | jq '.plan | length')"

echo "[$(date -u +%H:%M:%SZ)] Plan: $STEP_COUNT steps"
while IFS= read -r step; do
  STEP_NUM="$(echo "$step" | jq -r '.step')"
  STEP_AGENT="$(echo "$step" | jq -r '.agent')"
  STEP_LABEL="$(echo "$step" | jq -r '.label // .agent')"
  echo "  Step $STEP_NUM: $STEP_AGENT — $STEP_LABEL"
done < <(echo "$STEPS")

# Update task record with plan
TMP="$(mktemp)"
grep -v "\"id\":\"$TASK_ID\"" "$TASK_LOG" > "$TMP" || true
echo "$TASK_RECORD" | jq --argjson plan "$PLAN_JSON" '.plan = $plan.plan' >> "$TMP" \
  || { rm -f "$TMP"; echo "ERROR: jq failed updating task record" >&2; exit 1; }
mv "$TMP" "$TASK_LOG"

# Execute steps in order (sequential — parallel support can be added later)
while IFS= read -r step; do
  STEP_NUM="$(echo "$step" | jq -r '.step')"
  STEP_AGENT="$(echo "$step" | jq -r '.agent')"
  STEP_LABEL="$(echo "$step" | jq -r '.label // .agent')"

  echo ""
  echo "[$(date -u +%H:%M:%SZ)] Step $STEP_NUM/$STEP_COUNT: $STEP_LABEL"

  # Map agent id → script name
  case "$STEP_AGENT" in
    research)  SCRIPT="research_agent.sh" ;;
    strategy)  SCRIPT="strategy_agent.sh" ;;
    writer)    SCRIPT="writer_agent.sh" ;;
    creative)  SCRIPT="creative_agent.sh" ;;
    publisher) SCRIPT="publisher_agent.sh" ;;
    analytics) SCRIPT="analytics_agent.sh" ;;
    evolve)    SCRIPT="evolve_persona.sh" ;;
    *)
      echo "WARNING: unknown agent '$STEP_AGENT' — skipping step $STEP_NUM" >&2
      continue
      ;;
  esac

  # Extract focus if provided for research
  FOCUS_ARG=""
  if [ "$STEP_AGENT" = "research" ]; then
    FOCUS_ARG="$(echo "$step" | jq -r '.input.focus // empty' 2>/dev/null || true)"
  fi

  # Run agent script with project env vars injected
  export FACTORY_CONFIG FACTORY_OUTPUT FACTORY_DIRECTIVES FACTORY_ANALYTICS FACTORY_INBOX
  if [ -n "$FOCUS_ARG" ]; then
    "$SCRIPTS/$SCRIPT" "$FOCUS_ARG"
  else
    "$SCRIPTS/$SCRIPT"
  fi
  STEP_EXIT=$?

  if [ $STEP_EXIT -ne 0 ]; then
    echo "ERROR: step $STEP_NUM ($STEP_AGENT) failed (exit $STEP_EXIT)" >&2
    _fail_task "$TASK_ID" "$TASK_LOG" "step $STEP_NUM failed"
    exit 1
  fi

  echo "[$(date -u +%H:%M:%SZ)] Step $STEP_NUM complete."
done < <(echo "$STEPS")

_complete_task "$TASK_ID" "$TASK_LOG"
echo ""
echo "Task $TASK_ID complete for project '$PROJECT_NAME'."
