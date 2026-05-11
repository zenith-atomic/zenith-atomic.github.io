# TOOLS.md — OpenClaw Setup & Integrations

## APIs Configured

| Service | Status | Key Location |
|---|---|---|
| OpenAI (Codex) | ✅ Configured | ENV: OPENAI_API_KEY |
| Google Gemini | ✅ Configured | ENV: GEMINI_API_KEY |
| MiniMax | ✅ Configured | ENV: MINIMAX_API_KEY |
| Google Gmail/Drive/Sheets/Docs | ✅ Configured | ENV: GOOGLE_* |
| Telegram | ✅ Configured | Config file |
| Obsidian Vault | ✅ Working | `/home/ai/.openclaw/workspace/wiki/` |
| WhatsApp | ✅ Configured | Via OpenClaw channel |

## APIs Still Needed

| API | Priority | Purpose |
|---|---|---|
| Twilio | 🔴 High | Voice calls + SMS for receptionist |
| ElevenLabs | 🔴 High | Premium voice for outbound calls |
| Browserless | 🟡 Medium | Web research, JS-heavy sites |
| Stripe | 🔴 High | Billing for Nemoclaw customers |
| SerpAPI | 🟡 Medium | Unlimited Google search |
| Deepgram | 🟡 Medium | Transcription for voice calls |
| Pushover | 🟢 Low | Urgent alerts to phone |

## External Tools

| Tool | URL |
|---|---|
| Nemoclaw CRM | https://docs.google.com/spreadsheets/d/1W1ZsQzbhRv0Nsgs_jwEzF_fi_0xVaPE9i5uBi1oaKtU |
| Nemoclaw Knowledge Base | https://docs.google.com/document/d/1sJbu64Qr2J2q__NqJCV9Ja1vfa71Ic-TAEREzBrdyDQ |
| 25 Business Ideas | https://docs.google.com/spreadsheets/d/1MEAlMB6MdRgSg4VGr2-S7l1fg-LSZ-giovgTMPUnpWg |
| Nemoclaw Vault | `/home/ai/.openclaw/workspace/nemoclaw/` |

## TTS / Voice

- Preferred: ElevenLabs (key not yet set)
- Fallback: Edge TTS (free, no key needed)
- Current: OpenClaw default

## Scripts

- `scripts/reddit_json_scraper.py` — Reddit JSON scraping
- `scripts/reddit_market_research.py` — VOC pipeline
- `nemoclaw/research/02_reddit_voc/scrape.py` — Home services scrape
- `nemoclaw/research/02_reddit_voc/extract_concepts.py` — Concept extraction

## Workspace

- Root: `/home/ai/.openclaw/workspace/`
- Nemoclaw: `/home/ai/.openclaw/workspace/nemoclaw/`
- Wiki: `/home/ai/.openclaw/workspace/wiki/`
- Research: `/home/ai/.openclaw/workspace/research/`

## SSH

- dellrack (this machine): `172.20.19.228` / user: ai

## Gateway

- Local: `ws://127.0.0.1:18789` / Dashboard: `http://127.0.0.1:18789/`
- Systemd: running, enabled
