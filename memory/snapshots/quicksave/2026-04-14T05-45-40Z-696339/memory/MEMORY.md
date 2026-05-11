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

## Decisions
- 2026-04-14 — LanceDB is the canonical memory store, NexMem Core is the sole memory-write authority, graph is derived, and MCP/API is only the access layer.
- 2026-04-14 — OpenClaw should be a client of NexMem, not a second memory brain.

## Open long-term threads
- 2026-04-14 — Implement NexMem read/write/review commands and wire them cleanly into OpenClaw.
- 2026-04-14 — 2026-04-14 — test durable fact for /fact route
- 2026-04-14 — memory-system-test fact
