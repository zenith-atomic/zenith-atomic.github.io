#!/usr/bin/env bash
# Usage: project_init.sh <id> <name>
# Creates a new project directory under factory/projects/<id>/ and registers it in projects.json
set -euo pipefail

FACTORY="$HOME/.openclaw/workspace/factory"
PROJECTS_JSON="$FACTORY/projects.json"

PROJECT_ID="${1:-}"
PROJECT_NAME="${2:-}"

if [ -z "$PROJECT_ID" ] || [ -z "$PROJECT_NAME" ]; then
  echo "Usage: project_init.sh <id> <name>" >&2
  echo "Example: project_init.sh fitness-niche 'Fitness & Wellness'" >&2
  exit 1
fi

# Validate id: lowercase alphanumeric + hyphens only
if ! echo "$PROJECT_ID" | grep -qE '^[a-z0-9][a-z0-9-]*$'; then
  echo "ERROR: id must be lowercase alphanumeric with hyphens (e.g. 'fitness-niche')" >&2
  exit 1
fi

# Check for duplicate
if jq -e --arg id "$PROJECT_ID" '.projects[] | select(.id == $id)' "$PROJECTS_JSON" >/dev/null 2>&1; then
  echo "ERROR: Project '$PROJECT_ID' already exists" >&2
  exit 1
fi

PROJECT_DIR="$FACTORY/projects/$PROJECT_ID"
CONFIG_DIR="$PROJECT_DIR/config"
OUTPUT_DIR="$PROJECT_DIR/output"
DIRECTIVES_DIR="$PROJECT_DIR/directives"
ANALYTICS_DIR="$PROJECT_DIR/analytics"
INBOX_DIR="$PROJECT_DIR/inbox"
TASKS_DIR="$FACTORY/tasks/$PROJECT_ID"

# Scaffold directories
mkdir -p "$CONFIG_DIR" "$OUTPUT_DIR" "$DIRECTIVES_DIR" "$ANALYTICS_DIR" "$INBOX_DIR" "$TASKS_DIR"

# Copy template config from default project (or factory/config as fallback)
TEMPLATE_CONFIG="$(jq -r '.projects[] | select(.id=="default") | .config' "$PROJECTS_JSON" 2>/dev/null || echo "$FACTORY/config")"
for f in persona.yml pillars.yml platforms.yml schedule.yml; do
  if [ -f "$TEMPLATE_CONFIG/$f" ]; then
    cp "$TEMPLATE_CONFIG/$f" "$CONFIG_DIR/$f"
  fi
done

# Create empty directive files
for stage in research strategy writer creative publisher analytics; do
  touch "$DIRECTIVES_DIR/$stage.md"
done

# Initialize empty tasks log
echo "" > "$TASKS_DIR/tasks.jsonl"

# Register project in projects.json
TMP="$(mktemp)"
jq --arg id "$PROJECT_ID" \
   --arg name "$PROJECT_NAME" \
   --arg config "$CONFIG_DIR" \
   --arg output "$OUTPUT_DIR" \
   --arg directives "$DIRECTIVES_DIR" \
   --arg analytics "$ANALYTICS_DIR" \
   --arg inbox "$INBOX_DIR" \
   --arg created "$(date -u +%Y-%m-%d)" \
   '.projects += [{id:$id, name:$name, config:$config, output:$output, directives:$directives, analytics:$analytics, inbox:$inbox, created:$created}]' \
   "$PROJECTS_JSON" > "$TMP"
mv "$TMP" "$PROJECTS_JSON"

echo "Project '$PROJECT_NAME' created at $PROJECT_DIR"
echo "Next: edit $CONFIG_DIR/persona.yml to define the persona for this project"
