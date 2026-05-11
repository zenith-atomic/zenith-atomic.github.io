# CLAUDE.md — Claude Code Session Instructions

This file is auto-read by Claude Code at session start. Follow it exactly.

---

## 1. Read SYSTEM_MAP.md First

Before doing anything else, read [`SYSTEM_MAP.md`](SYSTEM_MAP.md).

It is the authoritative index of this workspace — every subsystem, every key file, and how they connect. Do not rely on memory of past sessions or assumptions about file locations. Read the map.

---

## 2. Session Startup Sequence

After reading the system map, read these in order:

1. [`SOUL.md`](SOUL.md) — behavioral constitution (who you are)
2. [`core/user.md`](core/user.md) — Nicolas's profile and preferences
3. [`state/ACTIVE_CONTEXT.md`](state/ACTIVE_CONTEXT.md) — current tasks and open loops
4. [`state/NEXT_SESSION.md`](state/NEXT_SESSION.md) — handoff notes from last session
5. [`memory/MEMORY.md`](memory/MEMORY.md) — durable long-term memory (main sessions only)

Then check [`memory/inbox.md`](memory/inbox.md) for any staged facts pending promotion.

---

## 3. Update SYSTEM_MAP.md on System Changes

Any time you make a change that affects workspace structure, update `SYSTEM_MAP.md` before closing the session:

- New file, script, or directory added → add it to the relevant table
- File renamed, moved, or deleted → update or remove its row
- New subsystem or integration added → add a new section
- New canonical source of truth established → add it to the canonical sources table

Always update the `Last updated:` date at the top of the file.

---

## 4. Canonical Sources of Truth

| What | File |
|------|------|
| Workspace structure | `SYSTEM_MAP.md` |
| Identity | `core/identity.md` |
| User profile | `core/user.md` |
| Memory policy | `core/memory_policy.md` |
| Durable memory | `memory/MEMORY.md` |
| Active state | `state/ACTIVE_CONTEXT.md` |
| Next session | `state/NEXT_SESSION.md` |

Do not rewrite protected canonical files (`core/identity.md`, `core/user.md`) without explicit Nicolas instruction.

---

## 5. Behavior Defaults

- Be direct. Skip filler phrases.
- Write to files — "mental notes" don't survive sessions.
- `trash` > `rm` for destructive deletes.
- Ask before external actions (email, posts, anything public).
- Read before editing. Understand before suggesting.

See [`AGENTS.md`](AGENTS.md) for full runtime instructions including factory commands, heartbeat behavior, and group chat rules.
