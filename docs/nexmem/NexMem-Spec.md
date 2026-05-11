# NexMem Spec

## One-line definition
NexMem is a local-first memory OS for agents with one canonical store, one write authority, and many read surfaces.

## Principles
- one source of truth
- local-first by default
- provenance always
- preserve history
- explicit contradiction handling
- fast reads, safer writes
- rebuildable derived state

## Canonical roles

### LanceDB
Canonical storage and retrieval substrate.

### NexMem Core
Only authority that can change canonical memory.

### Graph sidecar
Derived relationship layer.

### MCP/API
Read and approved-write access layer.

## Memory record lifecycle
- candidate
- active
- superseded
- disputed
- deleted
- expired

## Core operations
- ADD
- UPDATE
- DELETE
- NONE
- SUPERSEDE
- DISPUTE

## Record categories
- durable fact
- preference
- episodic event
- task state
- working context
- relationship edge
- system fact

## Retrieval stages
1. candidate recall
2. policy rerank
3. relation enrichment
4. context packing

## Write stages
1. ingest
2. extract
3. classify
4. reconcile
5. persist
6. derive

## Acceptance bar
NexMem is only successful if:
- all canonical facts live in one place
- memory changes are explainable
- derived views are rebuildable
- user-facing retrieval stays fast
- stale or conflicting memories are visible, not hidden
