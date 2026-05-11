# NexMem Architecture

## Thesis

NexMem is a local-first memory operating system for agents.

**One storage engine, one memory authority, many read interfaces.**

That means:
- **LanceDB** is the canonical storage system
- **NexMem Core** is the only authority allowed to decide memory writes and updates
- **Mem0-style logic** is implemented inside NexMem Core, not run as a competing runtime
- **Supermemory/MCP** is only an access surface, never the owner of memory state

## System of record

### LanceDB
LanceDB is the sole durable memory substrate.

It stores:
- vector embeddings
- full-text searchable text
- metadata
- timestamps
- provenance
- attachments and multimodal references
- versioned records

Why:
- hybrid retrieval
- vector + text + metadata in one place
- versioning for audit and rollback
- local-first operation

## Canonical memory engine

### NexMem Core
NexMem Core owns:
- fact extraction
- memory classification
- add / update / delete / ignore decisions
- contradiction resolution
- confidence scoring
- temporal policies
- expiry and forgetting
- profile synthesis rules
- provenance and audit logging

NexMem Core is the only write authority.

### Mem0 ideas to borrow
Adopt Mem0’s memory action model:
- ADD
- UPDATE
- DELETE
- NONE

Internally, NexMem Core should also support:
- SUPERSEDE
- DISPUTE

Why:
- deletion is too blunt for evolving truth
- supersede preserves history
- dispute preserves unresolved conflicts

## Derived relationship layer

### Graph sidecar
Use a graph layer only as derived context.

Store:
- entities
- aliases
- relationships
- event links
- people / org / project edges

Graph is not primary truth.
It should be rebuildable from canonical LanceDB records.

## Access and orchestration

### MCP / API
Expose NexMem through MCP or API adapters so clients can read and request approved writes.

Clients:
- OpenClaw
- Claude Code
- Cursor
- other MCP-compatible tools

Clients never write directly to storage.

## Canonical truth rule

Every memory item should have exactly one canonical record in LanceDB.
Everything else is derived:
- graph edges
- profile summaries
- context packs
- cached injections
- embeddings of reformulations
- client-facing summaries

## Write pipeline

incoming context → extraction → reconciliation → canonical record mutation → derived refresh

### Stages
1. ingest
2. fact extraction
3. classify
4. reconcile
5. persist canonical record
6. emit derived outputs

## Contradiction policy

Do not equate contradiction with deletion.

Use:
- **superseded** for evolving truths
- **disputed** for unresolved conflicts
- **deleted** only for explicit removals or bad extractions

## Temporal policy

Track:
- observed_at
- event_at
- valid_from
- valid_until
- last_confirmed_at
- last_accessed_at

Decay should affect retrieval rank and prompt inclusion, not silently erase truth.

## Retrieval model

### Stage 1, recall
From LanceDB:
- vector
- full text
- metadata filters
- hybrid rerank

### Stage 2, policy rerank
Use:
- recency
- confidence
- source quality
- explicitness
- contradiction state
- scope relevance

### Stage 3, relation enrichment
Pull graph neighbors:
- people
- projects
- dependencies
- adjacent events

### Stage 4, context packing
Produce prompt-ready context:
- minimal answer context
- memory summary
- profile hints
- open loops
- recent related episodes

## Performance model

### Sync path
Allowed in request path:
- retrieval
- reranking
- context pack assembly
- lightweight profile fetch

### Async path
Backgrounded:
- extraction-heavy writes
- contradiction reconciliation
- graph regeneration
- compaction
- stale memory review
- embedding refresh

## NexMem data model

Each memory record should conceptually carry:
- memory_id
- subject_scope
- memory_type
- status
- content
- normalized_content
- embedding
- keywords
- entities
- timestamp_event
- timestamp_observed
- valid_from
- valid_until
- confidence
- importance
- recency_weight
- provenance
- source_refs
- contradicts
- supersedes
- related_memory_ids
- policy_flags
- audit

## Bottom line

**LanceDB is the store. NexMem Core is the brain. Graph is derived. MCP is the door.**
