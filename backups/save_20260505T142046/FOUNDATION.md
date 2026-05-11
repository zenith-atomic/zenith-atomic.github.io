# Foundation Snapshot — 2026-05-05

Clean baseline established after bootstrap audit + slim.

## Bootstrap line counts at this point

| File | Lines |
|---|---|
| SYSTEM_MAP.md | 278 |
| AGENTS.md | 70 |
| CLAUDE.md | 10 (stub) |
| SOUL.md | 63 |
| HEARTBEAT.md | 8 |
| TOOLS.md | 63 |
| core/identity.md | 25 |
| core/user.md | 20 |
| core/memory_policy.md | 130 |

Cold-start session load: ~525 lines (down from ~1010+).

## Layout changes from prior state

- Deleted: root `IDENTITY.md`, `USER.md` (legacy unfilled scaffolds)
- Deleted: `WORKSTYLE.md` (merged into `SOUL.md`)
- Deleted: pip stderr junk `=1.0`, `=2.0`, `=4.0`
- Moved: `backup_restore_spec.md` → `docs/specs/`
- Created: `docs/runbooks/{factory,telegram-progress,research-scraping,heartbeat}.md`
- Slimmed: AGENTS.md (303 → 70), CLAUDE.md (66 → 10)
- Merged: WORKSTYLE.md content into SOUL.md
- Updated: SYSTEM_MAP with Top-Level Layout, Dispatch Layer, Gateway sections; wiki section reflects actual dir structure (articles instead of companies/products/concepts)

## Verified at snapshot

- All AGENTS.md internal refs resolve
- All CLAUDE.md refs resolve
- Bootstrap chain: SYSTEM_MAP → AGENTS → SOUL → core/* → state/* → memory/MEMORY.md
- Runbooks all present and on-demand only
