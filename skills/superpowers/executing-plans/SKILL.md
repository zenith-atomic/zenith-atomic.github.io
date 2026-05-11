---
name: executing-plans
description: Use when you have a written implementation plan to execute in a separate session with review checkpoints
---

# Executing Plans

**Announce at start:** "I'm using the executing-plans skill to implement this plan."

**Note:** Superpowers works much better with subagent support. If subagents are available, use subagent-driven-development instead.

## The Process

### Step 1: Load and Review Plan
1. Read plan file
2. Review critically — identify any questions or concerns
3. If concerns: raise them with human partner before starting
4. If no concerns: create TodoWrite and proceed

### Step 2: Execute Tasks
For each task:
1. Mark as in_progress
2. Follow each step exactly
3. Run verifications as specified
4. Mark as completed

### Step 3: Complete Development
After all tasks complete: use finishing-a-development-branch skill.

## When to Stop and Ask for Help
**STOP immediately when:**
- Hit a blocker (missing dependency, test fails, instruction unclear)
- Plan has critical gaps preventing starting
- Verification fails repeatedly

**Return to Review when:** Partner updates the plan, or fundamental approach needs rethinking.
