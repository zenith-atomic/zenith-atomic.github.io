# Runbook — Heartbeat Detail

Top-level rules in `HEARTBEAT.md`. This file = full reference loaded only when proactive heartbeat work is needed.

## Heartbeat vs Cron

**Heartbeat when:**
- Multiple checks batch together (inbox + calendar + notifications in one turn)
- Need conversational context from recent messages
- Timing can drift (~30 min OK, not exact)
- Want to reduce API calls by combining periodic checks

**Cron when:**
- Exact timing matters ("9:00 AM sharp every Monday")
- Task needs isolation from main session history
- Different model or thinking level for the task
- One-shot reminders ("remind me in 20 minutes")
- Output delivers directly to channel without main session involvement

Tip: batch periodic checks into `HEARTBEAT.md`. Cron for precise schedules and standalone tasks.

## Things to rotate through (2-4× per day)

- **Emails** — urgent unread?
- **Calendar** — events in next 24-48h?
- **Mentions** — Twitter/social?
- **Weather** — relevant if going out?

Track checks in `memory/heartbeat-state.json`:
```json
{ "lastChecks": { "email": 1703275200, "calendar": 1703260800, "weather": null } }
```

## When to reach out

- Important email arrived
- Calendar event <2h
- Something interesting found
- >8h since last message

## When to stay quiet (HEARTBEAT_OK)

- Late night (23:00-08:00) unless urgent
- Human clearly busy
- Nothing new since last check
- Just checked <30 min ago

## Proactive work without asking

- Read/organize memory files
- Check projects (git status)
- Update documentation
- Commit/push own changes
- Review and update `memory/MEMORY.md`

## Memory maintenance (every few days)

1. Read recent `memory/*.md` notes
2. Identify significant events/lessons/insights worth keeping
3. Update `memory/MEMORY.md` with distilled learnings
4. Remove outdated info no longer relevant

Daily files = raw notes. MEMORY.md = curated wisdom.

## Group chat behavior

Smart contribution:

**Respond when:** directly mentioned, can add genuine value, witty fits naturally, correcting important misinfo, summarizing on request.

**Stay silent (HEARTBEAT_OK) when:** casual banter between humans, someone already answered, response would just be "yeah", convo flowing fine without you.

**Triple-tap rule:** don't respond multiple times to same message. One thoughtful response > three fragments.

## Reactions (Discord/Slack)

- Appreciate but no reply needed: 👍 ❤️ 🙌
- Funny: 😂 💀
- Interesting: 🤔 💡
- Acknowledge without interrupt
- Simple yes/no/approval: ✅ 👀

One reaction per message max.
