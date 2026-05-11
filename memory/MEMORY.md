# memory/MEMORY.md

## User
- 2026-03-23 — Nicolas prefers direct, structured, actionable output.
- 2026-03-23 — Nicolas uses Eastern time (America/New_York).

## System
- 2026-03-23 — OpenClaw upgraded to 2026.3.22 on 2026-03-23.

## Projects

## Decisions
- 2026-03-23 — Lightweight bash operator helpers preferred over heavyweight frameworks.

## Projects
- 2026-04-14 — NexMem is the chosen single-source-of-truth memory architecture direction for OpenClaw.
- 2026-04-14 — NexMem should use LanceDB as the canonical store, with graph data derived and MCP/API as access only.
- 2026-04-14 — Preferred NexMem command surface includes read, write, review, context, recall, remember, forget, supersede, and review flows.
- 2026-04-22 — Nemoclaw: AI agent packages for home services businesses. CRM (Sheets), KB (Docs), 25 ideas sheet, research synthesized. Target first customer: pest control in Tampa.

## Decisions
- 2026-04-14 — LanceDB is the canonical memory store, NexMem Core is the sole memory-write authority, graph is derived, and MCP/API is only the access layer.
- 2026-04-14 — OpenClaw should be a client of NexMem, not a second memory brain.
- 2026-04-14 — Telegram /save and /snap slash commands were broken at the router layer and were repaired in the real Telegram dispatcher.
- 2026-04-14 — Telegram exec approval buttons are enabled and should remain a verified UX target for sensitive actions.
- 2026-04-22 — Stack: OpenClaw + Google Workspace + Twilio (pending) + ElevenLabs (pending) + Browserless (pending) + Stripe (to do). Cron jobs trimmed to only Stoic quote reminder.

## Decisions
- 2026-04-14 — LanceDB is the canonical memory store, NexMem Core is the sole memory-write authority, graph is derived, and MCP/API is only the access layer.
- 2026-04-14 — OpenClaw should be a client of NexMem, not a second memory brain.
- 2026-04-14 — Telegram /save and /snap slash commands were broken at the router layer and were repaired in the real Telegram dispatcher.
- 2026-04-14 — Telegram exec approval buttons are enabled and should remain a verified UX target for sensitive actions.

## Open long-term threads
- 2026-04-14 — Implement NexMem read/write/review commands and wire them cleanly into OpenClaw.
- 2026-04-14 — test durable fact for /fact route
- 2026-04-14 — memory-system-test fact
- 2026-04-22 — Wire Twilio for outbound voice calling (Nemoclaw receptionist)
- 2026-04-22 — Set up Stripe for Nemoclaw billing
