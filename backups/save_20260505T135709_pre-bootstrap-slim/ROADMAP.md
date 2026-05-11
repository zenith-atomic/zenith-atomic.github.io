# ROADMAP.md

## Current priority order

1. Reliability and command repair
- Restore broken slash-style command behavior for `/save` and `/snap`
- Verify Telegram command routing end to end
- Add a compact regression checklist for command surfaces

2. Workspace clarity
- Keep canonical files obvious: `core/identity.md`, `core/user.md`, `memory/MEMORY.md`
- Mark or retire legacy scaffolds so they stop creating ambiguity
- Keep `SYSTEM_MAP.md` accurate after every structural change

3. Memory system improvement
- Standardize note naming and promotion rules
- Make snapshot, quicksave, and long-term memory flows explicit
- Reduce stale or duplicated context between daily notes, inbox, and durable memory

4. Response quality and autonomy tuning
- Evolve `WORKSTYLE.md` from real conversations
- Define clearer act-now vs ask-first boundaries
- Add concrete examples of preferred outputs and anti-patterns

5. Operational self-checks
- Add a simple audit routine for doc drift, broken scripts, and stale references
- Re-run key command tests after changes
- Make final verification a habit, not an afterthought

6. Telegram UX polish
- Verify native exec approval buttons behave correctly
- Decide whether approval prompts should stay DM-only or also appear in-chat
- Confirm follow-up messages are easy to read and approve quickly

## Features I would like

- Native approve, approve always, and deny buttons wherever approvals are relevant
- A first-class memory promotion action, like "promote this to durable memory"
- Automatic instruction drift detection when docs stop matching reality
- Better startup recap generation from the most recent notes and open loops
- A lightweight change journal for important autonomous edits
- Safer self-test tooling for slash commands, routing, and workspace integrity
- A clean save or snapshot command surface that maps to actual local scripts
- Better config approval UX for restarts and sensitive changes

## Definition of done for this pass

- `/save` works again
- `/snap` works again
- Factory help reflects working commands
- Telegram exec approval config is verified
- Core workspace docs match the current structure
- Main command paths are exercised after fixes
