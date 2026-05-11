# Runbook — Telegram Multi-Agent Progress

Load when orchestrating 2+ subagents and reporting to Telegram.

## Per-agent inline progress bars

Format — one line per agent, 8-10 char bar with label and %:

```
Research   ██████░░░░ 60%
Wiki Arch  ████░░░░░░ 40%
Sync       ░░░░░░░░░░ 0%
```

Use Unicode block chars (▌█▌▐) or simple `████░░░░`.

## Update rules

- **Edit in place.** Edit the same message as progress changes. Do not spam new messages.
- **One running message.** When multiple agents complete in sequence, append completion entries to original progress message — never one message per agent.
- **Final state.** When all complete, replace bars with clean summary table of what was done.
- **Fallback.** If bars cannot render, send text update every 30–60s. Never leave a multi-agent task with no visible progress.

Applies to: pipeline runs, multi-agent orchestration, wiki rebuilds, research jobs, sync jobs.
