---
name: writing-skills
description: Use when creating new skills following best practices
---

# Writing Skills

## When to Write a New Skill
- Repeated pattern of work across projects
- Complex workflow that benefits from structured prompts
- Knowledge that should be reusable across sessions

## Skill Structure
```
skills/
  skill-name/
    SKILL.md          # Required: frontmatter + description + instructions
    [optional files]  # Templates, references, helpers
```

## SKILL.md Frontmatter
```yaml
---
name: skill-name
description: "Use when [trigger condition]. [What it does briefly]."
---
```

## SKILL.md Body
1. **Overview** — What the skill does and when to use it
2. **Core principle** — The single most important thing to know
3. **Process/The skill** — Step-by-step instructions
4. **Red Flags** — What never to do
5. **Integration** — How it connects to other skills

## Writing Guidelines
- Write for the moment of use — what does the agent need to know RIGHT NOW?
- Be specific about inputs, outputs, and step order
- Include exact commands with expected output where possible
- Avoid abstractions — show the actual prompt text, template, etc.
- Test the skill before committing it

## Testing Skills
1. Invoke the skill in a test session
2. Verify it triggers at the right moment
3. Verify output matches the expected format
4. Check for edge cases
