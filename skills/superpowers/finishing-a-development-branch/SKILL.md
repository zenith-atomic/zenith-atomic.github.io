---
name: finishing-a-development-branch
description: Use when implementation is complete, all tests pass, and you need to decide how to integrate the work
---

# Finishing a Development Branch

**Announce at start:** "I'm using the finishing-a-development-branch skill to complete this work."

## The Process

### Step 1: Verify Tests
Run project's test suite. If tests fail, stop and fix before proceeding.

### Step 2: Detect Environment
```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
```
Determines which menu to show.

### Step 3: Present Options

**Normal repo and named-branch worktree — 4 options:**
```
1. Merge back to <base-branch> locally
2. Push and create a Pull Request
3. Keep the branch as-is
4. Discard this work
```

**Detached HEAD — 3 options (no merge):**
```
1. Push as new branch and create a Pull Request
2. Keep as-is
3. Discard this work
```

### Step 4: Execute Choice
- **Option 1 (Merge):** Verify tests on merged result, cleanup worktree, delete branch
- **Option 2 (PR):** Push branch, create PR. Do NOT cleanup worktree.
- **Option 3 (Keep):** Report location, preserve worktree
- **Option 4 (Discard):** Confirm first with "type 'discard' to confirm", then force-delete

### Step 6: Cleanup Workspace
Only runs for Options 1 and 4. Always cleanup worktree before deleting branch.
