#!/usr/bin/env bash
# analytics_and_evolve.sh — Sunday evening combined job
# Runs analytics LLM report then evolves persona.
# Invoked by cron_run.sh so PATH and .env are already set.
set -euo pipefail

FACTORY="$HOME/.openclaw/workspace/factory/scripts"

echo "=== analytics_agent ==="
"$FACTORY/analytics_agent.sh"

echo "=== evolve_persona ==="
"$FACTORY/evolve_persona.sh"
