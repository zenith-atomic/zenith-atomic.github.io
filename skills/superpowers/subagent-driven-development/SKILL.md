---
name: subagent-driven-development
description: Use when executing implementation plans with independent tasks in the current session
---

# Subagent-Driven Development

**Core principle:** Fresh subagent per task + two-stage review (spec compliance → code quality) = high quality, fast iteration

**Continuous execution:** Do not pause to check in with your human partner between tasks. Execute all tasks from the plan without stopping. Only stop for: BLOCKED status, genuine ambiguity, or all tasks complete.

## When to Use
- Have implementation plan
- Tasks mostly independent
- Stay in this session
Otherwise use executing-plans (parallel session).

## The Process

Per task:
1. Dispatch implementer subagent with full task text + context
2. Implementer asks questions? → Answer and provide context
3. Implementer implements, tests, commits, self-reviews
4. Dispatch spec reviewer subagent (verify code matches spec)
5. Spec reviewer approves? → If no, implementer fixes → re-review
6. Dispatch code quality reviewer subagent
7. Code reviewer approves? → If no, implementer fixes → re-review
8. Mark task complete

After all tasks: dispatch final code reviewer → finishing-a-development-branch

## Model Selection
- **Mechanical implementation** (isolated functions, 1-2 files): cheap/fast model
- **Integration and judgment** (multi-file, pattern matching): standard model
- **Architecture and review**: most capable model

## Handling Implementer Status
- **DONE:** Proceed to spec compliance review
- **DONE_WITH_CONCERNS:** Read concerns, address correctness/scope issues, proceed
- **NEEDS_CONTEXT:** Provide missing context and re-dispatch
- **BLOCKED:** Assess blocker — provide more context, use more capable model, break task smaller, or escalate to human

## Red Flags
**Never:**
- Start on main branch without explicit user consent
- Skip reviews (spec OR code quality)
- Proceed with unfixed issues
- Dispatch multiple implementation subagents in parallel
- Make subagent read plan file (provide full text instead)
- Start code quality review BEFORE spec compliance passes

**If subagent asks questions:** Answer clearly before letting them proceed.
**If reviewer finds issues:** Implementer fixes → reviewer reviews again → repeat until approved.
