---
name: systematic-debugging
description: Use when diagnosing bugs or failures — 4-phase root cause process
---

# Systematic Debugging

**Core principle:** Systematic process over guessing.

## The 4-Phase Process

### Phase 1: Root Cause Tracing
1. Gather all evidence (logs, error messages, reproduction steps)
2. Isolate variables — what changed since it worked?
3. Form hypothesis: "I believe the bug is caused by X because Y"
4. Verify hypothesis experimentally

### Phase 2: Defense in Depth
Once a fix is found, ask:
- What other places might have this same bug?
- Is this a symptom of a systemic pattern?
- Should this be added to a regression test suite?

### Phase 3: Condition-Based Waiting
When waiting for intermittent failures:
- Can I reproduce on demand?
- Can I add instrumentation to catch it next time?
- Is there a related unit test I can strengthen?

### Phase 4: Verification Before Completion
After fixing:
1. Run the failing test — does it now pass?
2. Run the full test suite — did anything else break?
3. If possible, reproduce the original failure scenario manually
4. Document what was found and fixed

## Red Flags
- "It was probably a race condition" (without evidence)
- Changing code until tests pass without understanding why
- "It works on my machine"
