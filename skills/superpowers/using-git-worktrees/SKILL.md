---
name: using-git-worktrees
description: Use when starting feature work that needs isolation from current workspace or before executing implementation plans
---

# Using Git Worktrees

**Announce at start:** "I'm using the using-git-worktrees skill to set up an isolated workspace."

**Core principle:** Detect existing isolation first. Then use native tools. Then fall back to git.

## Step 0: Detect Existing Isolation
Before creating anything, check if already in an isolated workspace:
```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
BRANCH=$(git branch --show-current)
```
If `GIT_DIR != GIT_COMMON` (and not a submodule): already in a linked worktree. Skip to Step 3.

## Step 1: Create Isolated Workspace

### 1a. Native Worktree Tools (preferred)
Do you have a native worktree tool? If so, use it. Only use git worktree fallback if no native tool available.

### 1b. Git Worktree Fallback
Only if no native tool available. Create manually:
```bash
git worktree add "$path" -b "$BRANCH_NAME"
```
Directory priority: instruction file > `.worktrees/` > `worktrees/` > global path

**Safety:** Verify directory is git-ignored before creating project-local worktree:
```bash
git check-ignore -q .worktrees || git check-ignore -q worktrees
```

## Step 3: Project Setup
Auto-detect and run:
```bash
if [ -f package.json ]; then npm install; fi
if [ -f Cargo.toml ]; then cargo build; fi
if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
```

## Step 4: Verify Clean Baseline
Run tests to ensure workspace starts clean:
```bash
npm test / cargo test / pytest
```
If tests fail: report failures and ask whether to proceed.

## Report
```
Worktree ready at <full-path>
Tests passing (<N> tests, 0 failures)
Ready to implement <feature-name>
```
