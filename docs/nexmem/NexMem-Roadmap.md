# NexMem Roadmap

## Goal
Build one memory system with one source of truth.

## Phase 1, canonical foundation
- define LanceDB schema
- define record classes
- define provenance format
- define status lifecycle
- define tombstone / supersede behavior

## Phase 2, memory engine
- implement extraction pipeline
- implement reconciliation decisions
- implement temporal policy
- implement confidence scoring
- implement audit trail

## Phase 3, derived enrichment
- build graph sidecar
- generate entity edges from canonical records
- add profile synthesis
- add context pack assembler

## Phase 4, access surfaces
- expose read API
- expose MCP server
- add OpenClaw integration endpoints
- add controlled write entrypoints

## Phase 5, operations
- compaction jobs
- stale memory review
- contradiction review queue
- rollback and restore tooling
- observability and debug traces

## Phase 6, polish
- fast `/context` injection
- `/remember` or equivalent write command
- `/review` for disputed or stale items
- clean UI for approvals and memory status

## Success criteria
- one canonical record per fact
- no competing write authorities
- every derived view can be rebuilt
- conflicts are explicit, not hidden
- retrieval is fast and explainable
