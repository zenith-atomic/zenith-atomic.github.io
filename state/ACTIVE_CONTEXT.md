# state/ACTIVE_CONTEXT.md

current_tasks:
  - Nemoclaw: Build AI receptionist agent for home services (pending Twilio)
  - Wire outbound voice calling once Twilio is configured
  - First customer outreach: pest control shops in Tampa
open_loops:
  - Verify all Telegram commands work end-to-end after revamp
  - Set up Stripe for Nemoclaw billing
session_relevant_context:
  - Nemoclaw CRM: https://docs.google.com/spreadsheets/d/1W1ZsQzbhRv0Nsgs_jwEzF_fi_0xVaPE9i5uBi1oaKtU
  - Nemoclaw Knowledge Base: https://docs.google.com/document/d/1sJbu64Qr2J2q__NqJCV9Ja1vfa71Ic-TAEREzBrdyDQ
  - Voice: OpenClaw voice plugin loaded, Twilio account needed for outbound
  - Cron jobs cleaned: deleted 3 broken jobs, only Stoic quote at noon running
blockers:
  - Twilio account (user handling)
  - ElevenLabs key (user handling)
  - Browserless key (user handling)
last_updated_utc: 2026-05-09T18:10:00Z

recent_progress:
  - 2026-04-23 — Stoic quote cron confirmed working (Seneca sent)
  - 2026-04-27 — Stoic quote confirmed working (Musonius Rufus: comfort vs discipline)
  - Cron jobs cleaned: only noon Stoic quote active
  - 2026-05-09 — Fixed MiniMax thinking leak (reasoning_content leaking to chat)
  - 2026-05-09 — Wired /review and /review-smart in oc_dispatch.sh
  - 2026-05-09 — Aligned agent models to model_routing.yml (coder→owl-alpha, researcher→nemotron-super)
  - 2026-05-09 — Strengthened main agent fallback chain (codex→nemotron-super→ollama)
