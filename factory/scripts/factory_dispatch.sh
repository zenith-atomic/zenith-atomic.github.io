#!/usr/bin/env bash
set -euo pipefail

FACTORY="$HOME/.openclaw/workspace/factory"
SCRIPTS="$FACTORY/scripts"
ANALYTICS="$FACTORY/analytics"

# Parse subcommand — trim leading whitespace
RAW="${1:-help}"
CMD="$(echo "$RAW" | xargs)"

# If the full factory text was passed, extract subcommand
case "$CMD" in
  "brief"*)     SUBCMD="brief";     ARGS="${CMD#brief}" ;;
  "pursuit"*)   SUBCMD="pursuit";   ARGS="${CMD#pursuit}" ;;
  "research"*)  SUBCMD="research";  ARGS="${CMD#research}" ;;
  "strategy"*)  SUBCMD="strategy";  ARGS="" ;;
  "write"*)     SUBCMD="write";     ARGS="" ;;
  "visuals"*)   SUBCMD="visuals";   ARGS="" ;;
  "publish"*)   SUBCMD="publish";   ARGS="" ;;
  "analyze"*)   SUBCMD="analyze";   ARGS="" ;;
  "evolve"*)    SUBCMD="evolve";    ARGS="" ;;
  "run"*)       SUBCMD="run";       ARGS="" ;;
  "status"*)    SUBCMD="status";    ARGS="" ;;
  "dashboard"*) SUBCMD="dashboard"; ARGS="" ;;
  "ingest"*)    SUBCMD="ingest";    ARGS="${CMD#ingest}" ;;
  "compress"*)  SUBCMD="compress";  ARGS="${CMD#compress}" ;;
  "route"*)     SUBCMD="route";     ARGS="${CMD#route}" ;;
  "feedback"*)  SUBCMD="feedback";  ARGS="${CMD#feedback}" ;;
  "inbox"*)     SUBCMD="inbox";     ARGS="${CMD#inbox}" ;;
  "stage"*)     SUBCMD="stage";     ARGS="" ;;
  "approve"*)   SUBCMD="approve";   ARGS="${CMD#approve}" ;;
  "log"*)       SUBCMD="log";       ARGS="${CMD#log}" ;;
  "task"*)      SUBCMD="task";      ARGS="${CMD#task}" ;;
  "projects"*)  SUBCMD="projects";  ARGS="" ;;
  "project"*)   SUBCMD="project";   ARGS="${CMD#project}" ;;
  "save"*)      SUBCMD="save";      ARGS="" ;;
  "snap"*)      SUBCMD="snap";      ARGS="" ;;
  "help"|"")    SUBCMD="help"; ARGS="" ;;
  *)            echo "Unknown factory command: $CMD"; echo "Try: /factory help"; exit 1 ;;
esac

# Trim args
ARGS="$(echo "$ARGS" | xargs)"

case "$SUBCMD" in
  brief)
    # Run a creative brief through all studio agents in parallel
    BRIEF="$(echo "$ARGS" | xargs | sed "s/^['\"]//;s/['\"]$//")"
    [ -n "$BRIEF" ] || { echo "Usage: /factory brief \"<your creative brief>\"" >&2; exit 1; }
    ORCH="$FACTORY/orchestrator"
    [ -d "$ORCH/node_modules" ] || { echo "ERROR: Run 'npm install' in $ORCH first" >&2; exit 1; }
    exec node "$ORCH/index.js" brief "$BRIEF"
    ;;
  pursuit)
    # Research pursuits management
    PARGS="$(echo "$ARGS" | xargs)"
    PSUBCMD="$(echo "$PARGS" | awk '{print $1}')"
    PREST="$(echo "$PARGS" | cut -d' ' -f2-)"
    RESEARCH="$FACTORY/research"
    [ -d "$FACTORY/orchestrator/node_modules" ] || { echo "ERROR: Run 'npm install' in $FACTORY/orchestrator first" >&2; exit 1; }
    case "$PSUBCMD" in
      list)
        exec node "$RESEARCH/index.js" list ;;
      run)
        PID="$(echo "$PREST" | awk '{print $1}')"
        [ -n "$PID" ] || { echo "Usage: /factory pursuit run <id>" >&2; exit 1; }
        exec node "$RESEARCH/index.js" run "$PID" ;;
      run-due|due)
        exec node "$RESEARCH/index.js" run-due ;;
      create)
        PID="$(echo "$PREST" | awk '{print $1}')"
        PNAME="$(echo "$PREST" | awk '{print $2}')"
        PQUERY="$(echo "$PREST" | cut -d' ' -f3-)"
        [ -n "$PID" ] && [ -n "$PNAME" ] && [ -n "$PQUERY" ] || {
          echo "Usage: /factory pursuit create <id> \"<name>\" \"<query>\"" >&2; exit 1; }
        exec node "$RESEARCH/index.js" create "$PID" "$PNAME" "$PQUERY" ;;
      findings)
        PID="$(echo "$PREST" | awk '{print $1}')"
        N="$(echo "$PREST" | awk '{print $2}')"
        [ -n "$PID" ] || { echo "Usage: /factory pursuit findings <id> [n]" >&2; exit 1; }
        exec node "$RESEARCH/index.js" findings "$PID" ${N:+"$N"} ;;
      context)
        exec node "$RESEARCH/index.js" context ;;
      *)
        echo "Usage: /factory pursuit list | run <id> | run-due | create <id> \"<name>\" \"<query>\" | findings <id> [n] | context" >&2
        exit 1 ;;
    esac
    ;;
  research)
    exec "$SCRIPTS/research_agent.sh" "$ARGS"
    ;;
  strategy)
    exec "$SCRIPTS/strategy_agent.sh"
    ;;
  write)
    exec "$SCRIPTS/writer_agent.sh"
    ;;
  visuals)
    exec "$SCRIPTS/creative_agent.sh"
    ;;
  publish)
    exec "$SCRIPTS/publisher_agent.sh"
    ;;
  ingest)
    [ -n "$ARGS" ] || { echo "Usage: /factory ingest <url|pdf-path>"; exit 1; }
    exec "$SCRIPTS/wiki_ingest_cmd.sh" "$ARGS"
    ;;
  compress)
    WIKI_SCRIPTS="$HOME/.openclaw/workspace/wiki/scripts"
    exec "$WIKI_SCRIPTS/wiki_compress.sh" "$ARGS"
    ;;
  route)
    [ -n "$ARGS" ] || { echo "Usage: /factory route \"<task description>\""; exit 1; }
    WIKI_SCRIPTS="$HOME/.openclaw/workspace/wiki/scripts"
    exec "$WIKI_SCRIPTS/wiki_route.sh" "$ARGS"
    ;;
  feedback)
    WIKI_SCRIPTS="$HOME/.openclaw/workspace/wiki/scripts"
    exec "$WIKI_SCRIPTS/wiki_feedback.sh" "$ARGS"
    ;;
  inbox)
    [ -n "$ARGS" ] || { echo "Usage: /factory inbox <url or text> [tags]"; exit 1; }
    exec "$SCRIPTS/inbox_add.sh" "$ARGS"
    ;;
  stage)
    exec "$SCRIPTS/stage_posts.sh"
    ;;
  approve)
    AARGS=($ARGS)
    exec "$SCRIPTS/handle_approval.sh" "${AARGS[0]:-}" "${AARGS[1]:-}"
    ;;
  analyze)
    # Fetch real metrics first if fetch script exists, then run LLM analysis
    if [ -f "$SCRIPTS/fetch_analytics.sh" ]; then
      "$SCRIPTS/fetch_analytics.sh" || echo "WARNING: analytics fetch failed — running LLM analysis on existing data" >&2
    fi
    exec "$SCRIPTS/analytics_agent.sh"
    ;;
  evolve)
    exec "$SCRIPTS/evolve_persona.sh"
    ;;
  run)
    exec "$SCRIPTS/pipeline_runner.sh"
    ;;
  status)
    exec "$SCRIPTS/status.sh"
    ;;
  dashboard)
    HOSTNAME="$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'localhost')"
    echo "Dashboard: http://${HOSTNAME}:3700"
    ;;
  log)
    # Usage: /factory log <post-id> key=value key=value ...
    if [ -z "$ARGS" ]; then
      echo "Usage: /factory log <post-id> impressions=N engagements=N clicks=N"
      exit 1
    fi

    POST_ID="$(echo "$ARGS" | awk '{print $1}')"
    METRICS="$(echo "$ARGS" | cut -d' ' -f2-)"

    mkdir -p "$ANALYTICS"
    KPI_FILE="$ANALYTICS/kpi.jsonl"

    # Check if this post already has a KPI entry
    EXISTING=""
    if [ -f "$KPI_FILE" ]; then
      EXISTING="$(grep "\"id\":\"$POST_ID\"" "$KPI_FILE" || true)"
    fi

    if [ -n "$EXISTING" ]; then
      # Update existing entry
      UPDATED="$EXISTING"
      for KV in $METRICS; do
        KEY="${KV%%=*}"
        VAL="${KV#*=}"
        UPDATED="$(echo "$UPDATED" | jq --arg k "$KEY" --argjson v "$VAL" '.[$k] = $v')"
      done
      # Replace line in file
      TMP="$(mktemp)"
      grep -v "\"id\":\"$POST_ID\"" "$KPI_FILE" > "$TMP" || true
      echo "$UPDATED" >> "$TMP"
      mv "$TMP" "$KPI_FILE"
      echo "Updated KPIs for $POST_ID"
    else
      # Create new entry
      WEEK="$(date -u +%Y-W%V)"
      ENTRY="{\"id\":\"$POST_ID\",\"week\":\"$WEEK\",\"logged\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}"
      for KV in $METRICS; do
        KEY="${KV%%=*}"
        VAL="${KV#*=}"
        ENTRY="$(echo "$ENTRY" | jq --arg k "$KEY" --argjson v "$VAL" '.[$k] = $v')"
      done
      echo "$ENTRY" >> "$KPI_FILE"
      echo "Logged KPIs for $POST_ID"
    fi
    ;;
  task)
    # Usage: /factory task "<goal>" [project-id]
    if [ -z "$ARGS" ]; then
      echo "Usage: /factory task \"<goal>\" [project-id]" >&2
      echo "Example: /factory task \"research AI automation trends and write 3 LinkedIn posts\" ai-tools" >&2
      exit 1
    fi
    # Parse: first quoted arg is goal, second arg is optional project-id
    GOAL="$(echo "$ARGS" | sed 's/^ *//' | sed "s/^['\"]//;s/['\"]$//")"
    # Check if last word looks like a project-id (no spaces, alphanumeric-hyphens)
    PROJ_ARG=""
    if echo "$ARGS" | grep -qE '[[:space:]][a-z0-9][a-z0-9-]+$'; then
      PROJ_ARG="$(echo "$ARGS" | awk '{print $NF}')"
      GOAL="$(echo "$ARGS" | sed "s/ $PROJ_ARG$//" | sed 's/^ *//' | sed "s/^['\"]//;s/['\"]$//")"
    fi
    exec "$SCRIPTS/task_runner.sh" "$GOAL" ${PROJ_ARG:+"$PROJ_ARG"}
    ;;
  projects)
    # List all projects
    PROJECTS_JSON="$FACTORY/projects.json"
    DEFAULT="$(jq -r '.default' "$PROJECTS_JSON")"
    echo "Projects:"
    jq -r '.projects[] | "  \(.id)\t\(.name)"' "$PROJECTS_JSON" | while IFS=$'\t' read -r id name; do
      MARKER=""
      [ "$id" = "$DEFAULT" ] && MARKER=" (default)"
      echo "  $id — $name$MARKER"
    done
    ;;
  project)
    PARGS="$(echo "$ARGS" | xargs)"
    PSUBCMD="$(echo "$PARGS" | awk '{print $1}')"
    PREST="$(echo "$PARGS" | cut -d' ' -f2-)"
    case "$PSUBCMD" in
      new)
        PID="$(echo "$PREST" | awk '{print $1}')"
        PNAME="$(echo "$PREST" | cut -d' ' -f2-)"
        [ -n "$PID" ] && [ -n "$PNAME" ] || { echo "Usage: /factory project new <id> <name>" >&2; exit 1; }
        exec "$SCRIPTS/project_init.sh" "$PID" "$PNAME"
        ;;
      use)
        PID="$(echo "$PREST" | awk '{print $1}')"
        [ -n "$PID" ] || { echo "Usage: /factory project use <id>" >&2; exit 1; }
        PROJECTS_JSON="$FACTORY/projects.json"
        if ! jq -e --arg id "$PID" '.projects[] | select(.id == $id)' "$PROJECTS_JSON" >/dev/null 2>&1; then
          echo "ERROR: Project '$PID' not found" >&2; exit 1
        fi
        TMP="$(mktemp)"
        jq --arg id "$PID" '.default = $id' "$PROJECTS_JSON" > "$TMP" \
          || { rm -f "$TMP"; echo "ERROR: jq failed updating default project" >&2; exit 1; }
        mv "$TMP" "$PROJECTS_JSON"
        echo "Default project set to '$PID'"
        ;;
      *)
        echo "Usage: /factory project new <id> <name> | /factory project use <id>" >&2
        exit 1
        ;;
    esac
    ;;
  save)
    exec "$HOME/.openclaw/workspace/scripts/save_point.sh"
    ;;
  snap)
    exec "$HOME/.openclaw/workspace/scripts/quicksave.sh"
    ;;
  nexmem-context)
    exec "$WORKDIR/scripts/nexmem_context.sh"
    ;;
  help)
    cat <<'HELP'
Content Factory commands:

── STUDIO ORCHESTRATOR ──────────────────────────────────────────
  /factory brief "<text>"        - run brief through all studios in parallel
                                   e.g. /factory brief "I shipped a tool in 3 days"

── RESEARCH PURSUITS ────────────────────────────────────────────
  /factory pursuit list                       - list all configured pursuits
  /factory pursuit run <id>                   - run a pursuit now
  /factory pursuit run-due                    - run all pursuits that are due
  /factory pursuit create <id> "<n>" "<q>"    - create a new pursuit
  /factory pursuit findings <id> [n]          - show latest N findings
  /factory pursuit context                    - print compiled research context

── LEGACY PIPELINE ──────────────────────────────────────────────
  /factory research [topic]      - research trends & competitors
  /factory strategy              - generate weekly content plan
  /factory write                 - draft all posts from strategy
  /factory visuals               - generate image prompts
  /factory publish               - create posting checklist
  /factory analyze               - run analytics on KPIs
  /factory evolve                - update persona from analytics
  /factory run                   - run next pending pipeline stage
  /factory status                - show pipeline state

── CONTENT & QUEUE ──────────────────────────────────────────────
  /factory inbox <url|text>      - save reference/inspiration to inbox
  /factory stage                 - parse checklist into approval queue
  /factory approve <a> <id>      - approve or skip a queued post
  /factory log <id> <k=v>        - log post metrics

── WIKI & PROJECTS ──────────────────────────────────────────────
  /factory ingest <url|pdf>      - ingest URL or PDF into the wiki
  /factory compress [--dry-run]  - run wiki compression loop
  /factory route "<task>"        - get relevant context pack paths
  /factory task "<goal>" [proj]  - multi-step task runner
  /factory projects              - list all projects
  /factory project new <id> <n>  - create a new project
  /factory project use <id>      - set default project

── SYSTEM ────────────────────────────────────────────────────────
  /factory save                  - create a full save point backup
  /factory snap                  - quick snapshot
  /factory dashboard             - get dashboard URL
  /factory help                  - show this help
HELP
    ;;
esac
