# SYSTEM_MAP.md — OpenClaw Workspace

**Last updated:** 2026-05-09 (sandbox disabled for main agent; Browserless MCP; gbrain on postgres; full permissions)

Authoritative workspace index. Read first on every session. Update whenever files added/removed/renamed/repurposed.

---

## Top-Level Layout

```
~/.openclaw/workspace/
├── core/              identity, user profile, memory policy, model routing (canonical)
├── state/             ACTIVE_CONTEXT, NEXT_SESSION, runtime logs
├── memory/            durable MEMORY.md, inbox, raw notes, snapshots
├── docs/              runbooks/, specs/, nexmem/
├── factory/           content pipeline (research → strategy → writer → publisher → analytics)
├── wiki/              decision-engine knowledge base (topics, articles, playbooks)
├── scripts/           cron wrappers, Google auth, gdrive, health, backup/restore
├── bin/               local scratch utilities
├── logs/              cron and runtime logs
├── backups/           save_/backup_ timestamped snapshots
├── skills/            workspace-local skills
├── agents/            agent definitions
├── content-factory/   content-factory subsystem
├── daily-briefs/      daily brief output
├── newspaper/         newspaper output
├── nemoclaw/          Nemoclaw CRM data
├── receptionist/      receptionist agent
├── project-dragonfly/ project-dragonfly workspace
├── research/          research workspace
├── run-issues/        issue tracking
├── skillbridge/       skillbridge subsystem
└── *.md               AGENTS, CLAUDE, SOUL, SYSTEM_MAP, TOOLS, HEARTBEAT, ROADMAP
```

External reference: `~/bin/oc_dispatch.sh`, `~/bin/telegram_router.sh` (Telegram → workspace bridge).

---

## Dispatch Layer (`~/bin/`)

| File | Role |
|------|------|
| `~/bin/oc_dispatch.sh` | Primary command dispatcher. Routes: `note`, `fact`, `next`, `snap`, `save`, `status`, `model` |
| `~/bin/telegram_router.sh` | Telegram text → `oc_dispatch.sh`. Matches: `/status`, `/model <alias>`, `/save`, `/snap`, `/next`, `/note`, `/fact`, `/review`, `/review-smart`, `/factory` |

---

## Gateway / Service

| Item | Value |
|------|-------|
| Service | `systemctl --user openclaw-gateway.service` |
| Process | `node openclaw/dist/index.js gateway --port 18789` |
| Local URL | `ws://127.0.0.1:18789` / Dashboard `http://127.0.0.1:18789/` |
| Restart | `systemctl --user restart openclaw-gateway.service` |
| Config | `~/.openclaw/openclaw.json` (`gateway.auth.token`, `agents.defaults.model.*`, `channels.telegram`, `mcp.servers.*`) |

---

## Sandbox

Main agent runs **direct on host** (no Docker). Config: `agents.list[main].sandbox.mode = off`.

Subagents (factory-research etc.) still use Docker sandbox (`agents.defaults.sandbox.mode = all`).

To check: `openclaw sandbox explain` — expect `runtime: direct`.
To recreate a container: `openclaw sandbox recreate --agent <id> --force`.

---

## MCP Servers (`mcp.servers.*` in `openclaw.json`)

| Name | Command | Purpose |
|------|---------|---------|
| `browser` | `workspace/bin/browserless-mcp.sh` | Playwright MCP → Browserless cloud Chrome (`chrome.browserless.io`). Key in `.env` as `BROWSERLESS_API_KEY`. |
| `gbrain` | `/home/ai/.npm-global/bin/gbrain serve` | Knowledge brain MCP. Postgres engine (`postgresql://gbrain:***@127.0.0.1:5432/gbrain`). |
| `google-drive` | `node /home/ai/google-mcp-server/index.js` | Google Drive/Docs/Sheets (19 tools). Credentials from `.env`. |

**gbrain config:** `~/.gbrain/config.json` → `engine: postgres`. Wiki synced every 5 min via cron (`gbrain sync --repo wiki`). 72 pages imported from `workspace/wiki/`.

**Permissions:** `workspace/.claude/settings.json` — `Bash(*)`, `Read(*)`, `Write(*)`, `Edit(*)`. No prompt needed for any tool in direct sessions.

---

## Identity

| File | Role |
|------|------|
| `core/identity.md` | Zenith's identity — name, role, owner, priorities, voice. Protected canonical. |
| `core/user.md` | Nicolas's profile — preferences, timezone, context. Protected canonical. |
| `core/memory_policy.md` | Rules governing what gets stored, where, and how facts promote to durable memory. |
| `core/model_routing.yml` | Model selection rules (which model for which task type). |
| `SOUL.md` | Behavioral constitution — who Zenith is, how to act, core principles. |
| `TOOLS.md` | Local environment notes — device names, SSH aliases, TTS prefs, etc. |
| `ROADMAP.md` | Current improvement roadmap and definition of done for the active cleanup pass. |
| `docs/nexmem/` | NexMem architecture, roadmap, and OpenClaw integration specs. |
| `docs/runbooks/` | On-demand protocols (factory, telegram-progress, research-scraping, heartbeat). |
| `docs/specs/` | Specs (e.g. `backup_restore_spec.md`). |

---

## Session Guidance

| File | Role |
|------|------|
| `AGENTS.md` | Runtime instructions — startup, memory, red lines, runbook pointers. Slim (~70 lines). |
| `CLAUDE.md` | Stub — Claude Code load order: SYSTEM_MAP → AGENTS. |
| `SYSTEM_MAP.md` | **This file.** Workspace index. Read first, update on every system change. |
| `HEARTBEAT.md` | Short periodic checklist. Detail protocol → `docs/runbooks/heartbeat.md`. |

---

## Memory System

| File | Role |
|------|------|
| `memory/MEMORY.md` | Durable long-term memory. Curated, deduplicated facts only. |
| `memory/inbox.md` | Staging area — candidate facts awaiting promotion to MEMORY.md. |
| `memory/*.md` | Raw timestamped session and daily notes, for example `2026-04-13-2319.md`. |
| `memory/snapshots/YYYY-MM-DD/` | Timestamped exports before major migrations or bulk rewrites. |
| `memory/heartbeat-state.json` | Tracks last-check timestamps for email, calendar, weather (used by heartbeat). |

### Memory promotion flow
```
recent memory notes / inbox  →  (review)  →  memory/MEMORY.md
```
Promote only facts that are stable, specific, and useful across sessions.

---

## State

| File | Role |
|------|------|
| `state/ACTIVE_CONTEXT.md` | Current tasks, open loops, blockers, recent session context. |
| `state/NEXT_SESSION.md` | Handoff notes — what to pick up at next session start. |
| `state/active_notes.log` | Append-only runtime scratch log. |

---

## Factory System

The factory is an automated content and task pipeline.

| Path | Role |
|------|------|
| `factory/scripts/factory_dispatch.sh` | Main entrypoint — routes `/factory <subcommand>` calls. |
| `factory/scripts/` | All factory scripts (pipeline runner, agents, scheduler, inbox, etc.). |
| `factory/directives/` | Per-agent directive files (`creative.md`, `publisher.md`, `analytics.md`, `strategy.md`). |
| `factory/output/YYYY-Www/` | Weekly output — research, strategy, drafts. |
| `factory/dashboard/` | Express.js dashboard server for factory monitoring. |

### Key factory scripts

| Script | Role |
|--------|------|
| `factory_dispatch.sh` | Routes all `/factory` commands |
| `pipeline_runner.sh` | Runs the full content pipeline |
| `research_agent.sh` | Research phase |
| `strategy_agent.sh` | Strategy phase |
| `writer_agent.sh` | Writing phase |
| `creative_agent.sh` | Creative/ideation phase |
| `publisher_agent.sh` | Publishing/staging |
| `analytics_agent.sh` | Analytics fetch and reporting |
| `inbox_add.sh` / `inbox_fetch.py` | Inbox management |
| `stage_posts.sh` | Queue posts for approval |
| `wiki_ingest_cmd.sh` | Ingest URLs or PDFs into the wiki |

---

## Cron & Automation

| Path | Role |
|------|------|
| `scripts/cron_run.sh` | **Cron wrapper** — sets PATH (incl. npm-global), sources .env, per-job logs with UTC timestamps, Telegram alert on failure, log cap. Every cron job must use this. |
| `scripts/google_token.sh` | **Google auth helper** — sources .env, refreshes `GOOGLE_REFRESH_TOKEN`, outputs a fresh access token to stdout. Use this in any script that calls Google APIs (Docs, Drive, Sheets, Gmail, Calendar, etc.). |
| `scripts/gdrive.sh` | **Google Drive/Docs/Sheets CLI** — general-purpose tool for all Drive operations. Subcommands: `create-doc`, `create-sheet`, `create-folder`, `write-doc`, `append-doc`, `read-doc`, `sheet-append`, `sheet-read`, `sheet-write`, `sheet-clear`, `move`, `rename`, `delete`, `share`, `share-public`, `info`, `list`, `find`, `url`. Uses `google_token.sh` for auth. |
| `/home/ai/google-mcp-server/` | **Google Drive MCP server** — exposes 19 Drive/Docs/Sheets tools (`drive_*`) to the openclaw runtime via MCP. Registered in `openclaw.json` under `mcp.servers.google-drive`. Credentials injected via env at startup. |
| `scripts/analytics_and_evolve.sh` | Sunday combined job: runs analytics_agent then evolve_persona |
| `scripts/health_monitor.sh` | Lightweight health checks for gateway, Ollama, MCP processes, disk, and recent cron failures. |
| `scripts/backup_openclaw.sh` | Creates timestamped workspace backup archives and includes installed model inventory. |
| `scripts/restore_openclaw.sh` | Restores a backup archive into the workspace and restarts the gateway. |
| `logs/cron/<job_name>.log` | Per-job cron log. Start/output/result with UTC timestamps. Capped at 2000 lines. |
| `logs/cron/status.log` | Central status ledger — one START/OK/FAILED line per job run. Quick audit view. |

### Cron schedule (UTC — CRON_TZ is NOT respected by this cron daemon)

| UTC time | ET equivalent | Job |
|----------|--------------|-----|
| 08:00 daily | 4:00 AM EDT | `daily_snapshot` |
| 08:05 daily | 4:05 AM EDT | `wiki_lint` |
| 12:00 daily | 8:00 AM EDT | `fetch_analytics` |
| 13:03 daily | 9:03 AM EDT | `pipeline_runner` |
| every 15 min | every 15 min | `post_scheduler` |
| 00:07 Monday | 8:07 PM EDT Sunday | `analytics_sunday` |

### Adding a new cron job

Use `/cron-setup` skill — it has the full checklist.

---

## Wiki System

The wiki is a **decision engine organized by domain topics**, not a flat knowledge dump.

### Hierarchy

| Tier | Path | Role |
|------|------|------|
| A — Raw | `wiki/raw/` | Temporary pre-processed files. Auto-deleted after 7 days. |
| A — Inbox | `wiki/inbox/` | Staging area before ingest pipeline runs. |
| B — Topics | `wiki/topics/` | **Main nodes.** Domain hubs (e.g. home_services_ai). Everything links here. |
| B — People | `wiki/people/` | Named individual humans. |
| B — Articles | `wiki/articles/` | Long-form ingested write-ups (blueprints, playbooks). |
| B — Sources | `wiki/sources/` | Raw provenance records. Read-only after ingest. |
| C — Context Packs | `wiki/context_packs/` | Pre-built high-density injection bundles for task routing. |
| C — Playbooks | `wiki/playbooks/` | Repeatable executable strategies with feedback logs. |
| Index | `wiki/index.md` | Top-level wiki index. |
| Schema | `wiki/wiki_schema.md` | Page-format and tag spec. |
| Logs | `wiki/log.md`, `wiki/lint.log` | Ingest log, lint output. |

### Classification rule (quick reference)
- Named individual → `people/`
- Long-form write-up / playbook draft → `articles/`
- Domain organizing hub → `topics/`
- Re-usable injection bundle → `context_packs/`
- Repeatable executable strategy → `playbooks/`

### Page format (all Tier B pages)
Every ingested page outputs exactly: **Type / Topic / Summary / Key Facts / Relationships / Actions / Source**
Noise filter: only rejects truly zero-signal content (nav pages, login screens, ads). One useful fact = keep.

### Wiki Scripts

| Script | Role |
|--------|------|
| `wiki/scripts/wiki_ingest.sh` | Core ingestion — LLM extraction → structured page format |
| `wiki/scripts/wiki_fetch.sh` | Fetch a URL, HTML → Markdown, then ingest |
| `wiki/scripts/wiki_youtube.sh` | Fetch a YouTube transcript → Markdown, then ingest |
| `wiki/scripts/wiki_pdf.sh` | Convert a PDF → Markdown, then ingest |
| `wiki/scripts/wiki_linker.sh` | Link extractor / cross-reference builder |
| `wiki/scripts/wiki_lint.sh` | Linter for wiki consistency |
| `wiki/scripts/wiki_common.sh` | Shared library (exports WIKI_DIR, CONTEXT_PACKS_DIR, PLAYBOOKS_DIR, etc.) |
| `wiki/scripts/wiki_summarize_source.sh` | Generate structured summary block (TLDR/Key Points/Actionable Insight/Sections/Takeaways/Metadata) for a source file |
| `wiki/scripts/wiki_route.sh` | Classify a task → return 1–2 relevant context pack paths for injection |
| `wiki/scripts/wiki_compress.sh` | Daily loop: flag stale, find redundant, promote high-value → MEMORY.md, clean raw/ |
| `wiki/scripts/wiki_feedback.sh` | Log action outcomes → playbook Feedback Log table + global feedback_log.md |
| `wiki/scripts/wiki_query.sh` | Query interface over wiki content. |

### Factory commands
- `/factory ingest <url>` — ingest URL or PDF into the wiki
- `/factory compress [--dry-run]` — run compression loop
- `/factory route "<task>"` — get context pack paths for a task
- `/factory feedback --playbook <name> --attempt "..." --result "..." --insight "..."`

Ingest via: `/factory ingest <url>` or send a PDF directly in Telegram.
YouTube URLs are auto-detected by domain and routed to `wiki_youtube.sh`.

---

## Backup System

| Path | Role |
|------|------|
| `backups/backup_YYYYMMDDTHHMMSS/` | Full pre-migration backups (taken before any bulk rewrite). |
| `backups/save_YYYYMMDDTHHMMSS/` | Lightweight saves (taken before targeted changes). |

Rule: always create a timestamped backup before any normalization, migration, or bulk rewrite.

---

## Telegram Integration

| Component | Details |
|-----------|---------|
| Dispatcher | `oc_dispatch.sh` routes inbound Telegram commands |
| Router | `telegram_router.sh` → `oc_dispatch.sh` → workspace scripts |
| Slash commands | Bypass model via gateway patch in `pi-embedded-CzQCqSlH.js` |
| PDF ingest | Send PDF file to bot → auto-runs `wiki_ingest_cmd.sh <file_id> --telegram` |

---

## Canonical Sources of Truth

| What | Where |
|------|-------|
| Identity | `core/identity.md` |
| User profile | `core/user.md` |
| Memory policy | `core/memory_policy.md` |
| Model routing | `core/model_routing.yml` |
| Durable memory | `memory/MEMORY.md` |
| Active session state | `state/ACTIVE_CONTEXT.md` |
| Next session handoff | `state/NEXT_SESSION.md` |
| Workspace structure | `SYSTEM_MAP.md` ← this file |

---

## Update Protocol

Update on: new script/dir/component, rename/move/delete, subsystem change, new canonical source. Update `Last updated:` at top.
