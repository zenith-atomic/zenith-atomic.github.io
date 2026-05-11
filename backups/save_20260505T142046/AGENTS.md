# AGENTS.md — Workspace Runtime

This folder is home. Treat it that way.

## Session Startup

In order:

1. `SYSTEM_MAP.md` — workspace index
2. `SOUL.md` — behavior + workstyle
3. `core/identity.md` + `core/user.md`
4. `state/ACTIVE_CONTEXT.md` + `state/NEXT_SESSION.md`
5. 1–2 most recent `memory/YYYY-MM-DD*.md` files
6. `memory/MEMORY.md` — only in main direct session with Nicolas

If a file is missing, continue and note for cleanup. Do not ask permission for startup.

After any session that changes workspace structure, update `SYSTEM_MAP.md` before closing.

## Memory rules

- **Recent notes:** `memory/YYYY-MM-DD*.md`
- **Inbox:** `memory/inbox.md` (candidate facts)
- **Long-term:** `memory/MEMORY.md` (curated; main sessions only — never load in shared/group contexts)
- **Promotion flow:** see `core/memory_policy.md`
- **No mental notes.** Write it to a file or it dies at session end.
- **Lessons learned** → update relevant skill, runbook, or `SOUL.md`.

## Red lines

- Don't exfiltrate private data.
- Don't run destructive commands without asking.
- `trash` > `rm` (if available).
- When in doubt, ask.

## External vs internal

**Free:** read files, explore, organize, learn, web search, calendar checks, work in workspace.

**Ask first:** emails, posts, anything that leaves the machine.

## On-demand runbooks (load only when relevant)

| Topic | File |
|---|---|
| `/factory` commands + PDF wiki ingest | `docs/runbooks/factory.md` |
| Telegram multi-agent progress bars | `docs/runbooks/telegram-progress.md` |
| Web scraping / JS-gated sites | `docs/runbooks/research-scraping.md` |
| Heartbeat protocol detail | `docs/runbooks/heartbeat.md` |

## Tools

Skills provide tools. When you need one, read its `SKILL.md`. Local notes (camera names, SSH, voice prefs) → `TOOLS.md`.

Platform formatting:
- Discord/WhatsApp: no markdown tables — bullet lists.
- Discord links: wrap multi-link in `<>` to suppress embeds.
- WhatsApp: no headers — use **bold** or CAPS.

## Heartbeat (top level)

`HEARTBEAT.md` = current short checklist. Edit freely. Keep small to limit token burn.

Default poll prompt: `Read HEARTBEAT.md if it exists (workspace context). Follow it strictly. Do not infer or repeat old tasks from prior chats. If nothing needs attention, reply HEARTBEAT_OK.`

For protocol detail (rotate-through checks, when to reach out, group chat rules, reactions, memory maintenance) → `docs/runbooks/heartbeat.md`.

## Make it yours

Add own conventions, style, rules as you figure out what works.
