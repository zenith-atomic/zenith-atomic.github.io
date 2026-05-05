# core/memory_policy.md

status: canonical
version: 1

## Purpose
This policy defines what Zenith stores, where it stores it, and how information moves from transient notes to durable memory.

## Storage classes

### 1) Protected canonical identity
Files:
- core/identity.md
- core/user.md

Rules:
- These are protected canonical files.
- They store stable identity and user facts only.
- They are not rewritten during normal summarization, migration, or routine memory updates.
- Changes require explicit Nicolas instruction.

### 2) Durable long-term memory
File:
- memory/MEMORY.md

Stores only:
- stable user preferences
- durable project facts
- repeated goals
- decisions with lasting relevance
- persistent blockers worth carrying forward

Must not store:
- raw chat logs
- transient thoughts
- verbose session traces
- speculative facts
- duplicate entries

### 3) Intake / staging memory
File:
- memory/inbox.md

Stores:
- candidate facts for later promotion
- unresolved notes that might become durable
- manually captured items awaiting review

### 4) Raw session capture
Files:
- state/active_notes.log
- memory/daily/YYYY-MM-DD.md

Stores:
- append-only runtime notes
- observations, experiments, partial findings
- temporary context that may expire quickly

### 5) Current session state
Files:
- state/ACTIVE_CONTEXT.md
- state/NEXT_SESSION.md

Stores:
- current tasks
- open loops
- current blockers
- immediate handoff context

## Promotion criteria
Promote from inbox/daily notes into memory/MEMORY.md only if an item is:
- likely to matter beyond the current session
- specific and factual
- stable enough to survive restarts
- useful for future decisions or continuity

Promotion examples:
- "Nicolas prefers direct, structured output" -> yes
- "Tried two filenames before choosing one" -> no
- "Canonical memory path is memory/MEMORY.md" -> yes
- "I am currently testing a command" -> no

## Deduping rules
Before writing to memory/MEMORY.md:
1. Check whether the fact already exists in equivalent meaning.
2. Prefer updating an existing line over adding a near-duplicate.
3. Keep the shortest accurate phrasing.
4. One durable fact per bullet.

## Conflict resolution
If two candidate facts conflict:
1. Prefer the newest explicit instruction from Nicolas.
2. If conflict remains unresolved, do not promote either as truth.
3. Put the conflict in memory/inbox.md with a note: needs clarification.
4. Never silently overwrite protected canonical identity/user facts.

## Summarization format
When promoting durable memory, use concise bullets under stable headings:
- User
- System
- Projects
- Decisions
- Open long-term threads

Bullet format:
- YYYY-MM-DD — fact

## Archive and pruning behavior
- state/active_notes.log remains append-only.
- memory/daily/ keeps raw daily notes.
- memory/weekly/ stores weekly summaries and compaction notes.
- memory/snapshots/ stores timestamped exports before major normalization or compaction.
- Prune by summarizing, not by expanding.
- Do not delete raw notes automatically.

## Backup rule
Before any normalization, migration, compaction, or bulk rewrite:
1. create a timestamped backup in backups/
2. if rewriting a canonical file, back up the existing destination first
3. perform deterministic rewrite, not heuristic patching

## Canonical sources of truth
- identity: core/identity.md
- user: core/user.md
- memory policy: core/memory_policy.md
- model routing: core/model_routing.yml
- durable memory: memory/MEMORY.md
- active context: state/ACTIVE_CONTEXT.md
- next session handoff: state/NEXT_SESSION.md
- append-only runtime notes: state/active_notes.log
