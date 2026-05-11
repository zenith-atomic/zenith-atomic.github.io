# SkillBridge — Mobile Control Center for OpenClaw

## Concept & Vision

A premium mobile-first operator dashboard that feels like a live mission-control surface — not a menu app, not a vibe-coded prototype. Think Linear meets Bloomberg Terminal: data-forward, dense but breathable, with a live operational feel. Every number pulses. Every status glows. Every tap has weight.

---

## Design Language

### Aesthetic
**Reference:** Linear + Bloomberg Terminal + Tao Stats
Deep dark command-center palette, refined surfaces with layered depth, live pulsing indicators, monospace numbers for that terminal feel.

### Colors
```
Background:       #080810  (deep, rich dark)
Surface:          #10101a  (card backgrounds)
Surface-2:        #18182a  (elevated surfaces)
Surface-3:        #20203a  (highest elevation)
Border:           #1e1e32  (subtle dividers)
Border Bright:     #2a2a44  (interactive borders)
Accent:           #6366F1  (indigo)
Accent-2:         #818cf8  (lighter indigo for text)
Accent Glow:      rgba(99,102,241,0.30)
Accent Dim:       rgba(99,102,241,0.12)
Success:          #10B981  (emerald)
Success Dim:      rgba(16,185,129,0.12)
Warning:          #F59E0B  (amber)
Warning Dim:      rgba(245,158,11,0.12)
Danger:           #EF4444  (red)
Danger Dim:       rgba(239,68,68,0.12)
Text:             #F0F0FA  (near-white with blue tint)
Text Dim:         #6B6B8A  (muted labels)
Text Dimmer:      #3a3a5c  (very muted)
```

### Typography
- **UI Font:** Inter (Google Fonts) — weights 400, 500, 600, 700, 800
- **Numbers/Metrics:** JetBrains Mono — all numeric values, times, codes
- **Scale:** 9px labels → 11px captions → 13px body → 15px card titles → 20px section heads → 28px hero metrics

### Spatial System
- 8px base grid
- Touch targets: minimum 44px
- Border radius: 6px (sm), 10px (default), 14px (lg), 16px (xl)
- Generous padding on cards (14–16px)
- Compact spacing between related elements

### Motion
- `transition: all 0.15s ease` on all interactive elements
- `fade-up` animation on view switch (0.25s ease)
- Pulsing ring animation on live status dots (2s ease-in-out infinite)
- Shimmer skeleton loading (1.5s infinite)
- Modal sheets slide up with `cubic-bezier(0.32, 0.72, 0, 1)`
- Glow pulse on active navigation indicator

---

## Layout

### Top Bar (52px, sticky)
- Brand icon + "SkillBridge" name (left)
- Live pulsing dot + real-time clock (right) — clock updates every second, monospace font
- Frosted glass backdrop blur

### Sidebar (68px, fixed left)
- 6 navigation items: Home ⚡, CRM 📋, Cal 📅, Content ✍️, Social 🌐, Agents 🤖
- Active state: filled background with indigo tint + glowing left border indicator
- Icon + label layout
- Subtle pulse animation on the active indicator

### Views (scrollable, full-width)
Each view is padded 16px with 80px bottom clearance for mobile ergonomics.

---

## Home Dashboard — The Hero View

### Metric Strip (4-column grid)
Four metric cards immediately visible on load:
```
┌──────────┬──────────┬──────────┬──────────┐
│ ● CRM   │ ● Calls  │ ● Social │ ● Email  │
│  3      │  0       │  ●       │  4       │
│ appts   │  today   │  live    │  inbox   │
└──────────┴──────────┴──────────┴──────────┘
```
- Each card: pulsing status dot, large JetBrains Mono number, small uppercase label
- Top border accent color (green=success, amber=warning, red=danger, indigo=neutral)
- Live data from `/api/metrics` on load + every 30s

### Today's Pulse (2-column grid)
- **Left — Next Appointment:** Shows next scheduled with countdown ("in 2h 14m"), contact name, time. If none: 🎉 "Clear day" empty state.
- **Right — Recent Activity:** Mini timeline of last 4 events (📅 appt, 📞 call, ✉️ email, 🤖 agent), each with icon, title, time

### Active Agents (horizontal scroll strip)
- Horizontally scrollable row of agent cards
- Each card: avatar emoji, name, runtime badge, pulsing dot if live, key metric ("2 calls today" or "idle 3h")
- Data from `/api/agents/list`

### Quick Actions (2×2 grid)
Compact icon+label buttons: 📞 Call Nic | 📋 CRM | 📅 Calendar | ✉️ Email

---

## CRM View — Data-Forward

### Search + Filter
- Search bar with live filtering (name, phone, email, business)
- Filter chips: All | New | Qualified | Follow-up | Contacted
- Active filter highlighted in accent color

### Lead List
- Each lead: initials avatar + name + phone/email (truncated) + status badge + appointment date
- Tap to open slide-up sheet with full details
- Skeleton loading rows on initial load
- Empty state when no leads match filter

### Lead Detail Sheet (bottom slide-up)
```
┌─────────────────────────────┐
│  ─── (drag handle)          │
│  John Smith                 │
│  Acme Plumbing              │
├─────────────────────────────┤
│  Phone        Email          │
│  555-1234     john@mail.com  │
│  Status       Appointment    │
│  [New]        May 1 · 9am   │
│  Business                   │
│  Acme Plumbing LLC           │
├─────────────────────────────┤
│  [📞 Call] [✉️ Email] [🔍 Research] │
└─────────────────────────────┘
```
- Actions: Call (triggers outbound), Email (opens compose modal with to: pre-filled), Research (opens Google search)
- Result message shown in sheet

---

## Calendar View

### Week Strip (7-column grid)
- Navigate prev/next week
- Today highlighted with accent border + tinted background
- Events shown as time+title chips, max 2 shown, "+N more" overflow

### Today's Timeline
- Time column (hour:minute AM/PM in mono) + vertical bar + event card
- Events happening "now" get glowing accent border
- Tapping event card opens Google Calendar link

---

## Content View

### Profile Selector (horizontal scroll)
- 5 profiles: Money Matters, TechByte, FitFuel, Hustle Lab, FocusFlow
- Active profile has accent border
- Selecting auto-sets the niche dropdown

### Script Generator
- Niche dropdown + count dropdown (grid 2-col)
- Generate button → loading state → script cards
- Each script card: hook-type badge (top-right), prominent hook text, body, CTA, copy button
- Copy individual or "Copy All Scripts"

### Image Generator
- Text prompt + style dropdown + generate button
- Shows generated image in 1:1 preview grid
- Error state if generation fails

---

## Social View

### Connected Accounts (platform cards)
- Twitter, Instagram, TikTok, YouTube
- Each: colored icon, name, status, + Connect / ● Connected badge
- Tap → info about headless browser auth (coming soon)

### Post Now
- Platform selector + textarea + Post Now button
- Posts via OpenCLI headless browser (when connected)

---

## Agents View

### Quick Launch Presets (2×2 grid)
- CRM Research, Weekly Brief, Outreach Sequence, Reddit VOC
- Each: icon, name, one-line description
- Tap → spawns preset task via API

### Custom Task
- Runtime selector (subagent/ACP) + task description input + Spawn button

### Active Agents List
- Real-time list from OpenClaw sessions
- Avatar, name, runtime badge, status badge, key metric
- Refresh on view enter

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/status` | Overall health of all tools |
| GET | `/api/metrics` | Aggregated metrics for home dashboard |
| GET | `/api/activity` | Recent activity feed |
| GET | `/api/crm/leads` | Full lead list from Google Sheets |
| GET | `/api/crm/appointments` | Upcoming appointments |
| GET | `/api/calendar/today` | Today's calendar events |
| GET | `/api/calendar/next` | Next week's calendar events |
| GET | `/api/gmail/unread` | Unread emails |
| GET | `/api/agents/list` | Active OpenClaw agents/sessions |
| POST | `/api/agents/spawn` | Spawn a new agent task |
| POST | `/api/content/generate` | Generate content scripts |
| POST | `/api/image/generate` | Generate image (pipeline pending) |
| POST | `/api/email/send` | Send email via Gmail API |
| POST | `/api/social/post` | Post to social platform |
| POST | `/api/call/nic` | Trigger outbound call |
| POST | `/api/agent/generate` | AI email composition |

---

## Technical Notes

- Server: Express.js on port 3080
- Frontend: Vanilla HTML/CSS/JS, no build step
- Google Auth: OAuth via `utils/google-auth.js`
- Fonts: Inter + JetBrains Mono via Google Fonts CDN
- Auth: HTTP Basic (`demo` / `skillbridge`)
- All API calls from browser → SkillBridge server → Google/OpenClaw APIs
