# SYSTEM_MAP.md — OpenClaw Workspace

**Last updated:** 2026-05-01 (config hardening, health monitor cleanup, backup/restore scripts)
**Maintained by:** Zenith (update this file whenever system structure changes)

---

## Purpose

This is the authoritative map of the workspace. Read it first on every session. Update it whenever files are added, removed, renamed, or repurposed.

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
| `WORKSTYLE.md` | Nicolas-specific response and execution preferences. Operational guidance. |
| `ROADMAP.md` | Current improvement roadmap and definition of done for the active cleanup pass. |
| `docs/nexmem/` | NexMem architecture, roadmap, and OpenClaw integration specs. |
| `IDENTITY.md` | Legacy scaffold identity file. Not canonical. Keep only if intentionally used. |
| `USER.md` | Legacy scaffold user profile file. Not canonical. Keep only if intentionally used. |

---

## Session Guidance

| File | Role |
|------|------|
| `AGENTS.md` | Primary runtime instructions — startup sequence, memory rules, factory commands, heartbeat behavior. |
| `CLAUDE.md` | Claude Code-specific startup instructions — read SYSTEM_MAP first, update on system changes. |
| `SYSTEM_MAP.md` | **This file.** Workspace structure index. Read first, update on every system change. |
| `HEARTBEAT.md` | Periodic task checklist for background agent. Keep minimal to limit token burn. |

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
| B — Topics | `wiki/topics/` | **Main nodes.** Domain-level hubs derived from content (e.g. home_services_ai, ai_search_optimization). Everything links here. |
| B — People | `wiki/people/` | Named individual humans. |
| B — Companies | `wiki/companies/` | Organizations and businesses. |
| B — Products | `wiki/products/` | Named software, tools, platforms, hardware. |
| B — Concepts | `wiki/concepts/` | Abstract ideas, frameworks, methodologies, trade categories. |
| B — Sources | `wiki/sources/` | Raw provenance records. Read-only after ingest. |
| C — Context Packs | `wiki/context_packs/` | Pre-built high-density injection bundles for task routing. |
| C — Playbooks | `wiki/playbooks/` | Repeatable executable strategies with feedback logs. |

### Classification rule (quick reference)
- Named individual → `people/`
- Organization that makes things → `companies/`
- Named tool/software you USE → `products/`
- Abstract idea, framework, practice → `concepts/`
- Domain organizing hub → `topics/`

### Page format (all Tier B pages)
Every ingested page outputs exactly: **Type / Topic / Summary / Key Facts / Relationships / Actions / Source**
Noise filter: only rejects truly zero-signal content (nav pages, login screens, ads). One useful fact = keep.

### Wiki Test UI

| Path | Role |
|------|------|
| `wiki/test_ingest/server.py` | Local test server (port 3701) — UI to submit URLs, PDFs, and Markdown files for ingest. Run: `python3 wiki/test_ingest/server.py` |

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

Update this file when:
- A new script, directory, or system component is added
- A file is renamed, moved, or deleted
- A subsystem (factory, wiki, telegram, etc.) changes meaningfully
- A new canonical source of truth is established

Format: update the relevant table row or add a new section. Append `Last updated: YYYY-MM-DD` at the top.
