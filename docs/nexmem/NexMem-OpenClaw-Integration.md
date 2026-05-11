# NexMem + OpenClaw Integration

## Integration goals

- make OpenClaw a first-class client of NexMem
- keep memory writes routed through one authority
- keep user-facing retrieval fast
- preserve auditability and rollback

## Proposed commands

### Read
- `/context` → return packed memory + session context
- `/recall <query>` → search canonical memory
- `/profile` → show synthesized profile snapshot

### Write
- `/remember <text>` → send candidate memory to NexMem Core
- `/forget <id>` → mark record deleted or tombstoned
- `/supersede <id> <text>` → replace an older fact cleanly

### Review
- `/review` → show stale, disputed, low-confidence, or conflicting items
- `/memory-status` → show memory health and index status

## OpenClaw behavior

OpenClaw should only do:
- accept input
- call NexMem Core
- render approved results
- never mutate canonical memory directly

## Internal flow

Telegram / OpenClaw input
→ command parse
→ NexMem Core
→ LanceDB write or read
→ derived refresh
→ response

## Data contracts

### Read contract
- summary
- supporting facts
- confidence
- provenance
- recency
- conflict notes

### Write contract
- input text
- extracted candidates
- decision
- reason
- affected records
- audit id

## UX requirements

- fast retrieval for chat use
- clear approval prompts for sensitive writes
- explicit conflict surfacing
- simple language in user-facing messages

## Non-goals

- multiple competing memory brains
- silent overwrite without trace
- direct client writes to storage
- opaque “magic” profile updates
