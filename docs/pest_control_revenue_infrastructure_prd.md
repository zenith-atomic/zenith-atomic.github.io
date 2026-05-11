# PRD: Pest Control Revenue Infrastructure

## 1. Product Summary
Build an AI-powered revenue recovery system for pest control companies that captures missed leads, follows up on quotes, requests reviews, and reactivates stale opportunities. The product is designed to increase booked jobs from traffic and leads the company already has, with a clear path from service-first implementation to reusable software.

## 2. Problem Statement
Pest control businesses often lose revenue because:
- missed calls are not returned quickly
- web leads are not followed up consistently
- quotes go cold without reminders
- review requests are manual or inconsistent
- old customers and dormant leads are not reactivated
- owners lack visibility into response time and conversion loss

These failures are expensive because the business already paid to acquire the lead.

## 3. Target Customer
### Primary
- local pest control companies
- owner-operated or small multi-crew businesses
- 1-25 employees
- revenue dependent on calls, web forms, and repeat service

### Secondary
- HVAC
- roofing
- plumbing
- med spa
- dental

## 4. Core Value Proposition
Recover booked jobs from leads the business already paid for.

### Revenue benefits
- more booked jobs
- faster response times
- fewer lost leads
- more reviews
- higher local search trust
- more reactivated customers

## 5. Product Goals
### Business goals
- close first paid client within 30 days
- prove measurable revenue lift in pilot accounts
- turn service delivery into reusable software

### User goals
- respond to new leads fast
- never forget to follow up
- convert old quotes into booked jobs
- request more reviews automatically
- see where revenue is being lost

## 6. Non-Goals
- full CRM replacement in MVP
- complex marketing automation suite
- generic AI chatbot for everything
- deep accounting or invoicing system
- multi-industry platform on day one

## 7. MVP Scope
### Must have
1. missed-call text back
2. lead intake capture
3. quote follow-up automation
4. review request automation
5. stale lead reactivation
6. simple dashboard/reporting
7. manual override and editing
8. logging of every touchpoint

### Nice to have
- call summaries
- AI-generated reply drafts
- owner task suggestions
- lead scoring
- appointment booking integration
- pipeline stage tracking

## 8. User Roles
### Owner
- wants more booked jobs and better visibility
- cares about money, not tech

### Office manager / dispatcher
- wants less manual follow-up
- needs clarity on next actions

### Technician / field lead
- may trigger review requests or notes

## 9. Main User Journeys
### Journey 1, missed call recovery
1. customer calls and nobody answers
2. system sends text back within minutes
3. system asks intent and captures lead
4. office sees lead in dashboard
5. follow-up continues until booked or closed

### Journey 2, quote follow-up
1. quote marked as sent
2. system starts timed follow-up sequence
3. customer receives reminders
4. replies are logged
5. owner sees quote conversion status

### Journey 3, review request
1. job completed
2. system sends review request
3. satisfied customer gets link
4. review count rises over time

### Journey 4, dormant lead reactivation
1. old lead list imported
2. system sends reactivation sequence
3. interested leads are surfaced
4. booked jobs are tracked

## 10. Functional Requirements
### Lead capture
- ingest from web forms, missed calls, or CSV upload
- store name, phone, email, source, service type, notes, status

### Follow-up engine
- timed sequences by lead type
- editable templates
- stop rules when lead replies or books

### Review automation
- trigger after completed job
- customizable timing
- review link insertion

### Dashboard
- new leads
- contacted leads
- replies
- booked jobs
- quote follow-up status
- review request status
- reactivated leads

### Notifications
- alert owner when a hot lead replies
- flag stale opportunities
- surface unanswered leads

### Admin tools
- edit templates
- pause sequences
- reassign leads
- review logs
- manually mark outcome

## 11. Data Objects
### Lead
- id
- name
- phone
- email
- source
- service type
- city
- status
- last contact time
- owner assigned
- notes

### Conversation
- lead id
- channel
- message body
- timestamp
- direction
- outcome

### Sequence
- name
- purpose
- steps
- timing
- active/inactive

### Review request
- job id
- send time
- status
- review link

## 12. Integrations
### Phase 1
- Gmail
- Google Sheets
- Google Drive
- browser research / Maps
- SMS or calling tool

### Phase 2
- CRM
- web forms
- scheduling tool
- calendar
- payment / invoicing tool

## 13. AI Components
- lead intake triage
- follow-up draft generation
- reply classification
- summary generation
- opportunity scoring
- suggested next action

## 14. Metrics
### Revenue metrics
- booked jobs
- quote-to-book rate
- reactivated lead rate
- review conversion rate
- revenue recovered

### Efficiency metrics
- response time
- follow-up completion rate
- no-response rate
- manual tasks saved

### Product metrics
- active sequences
- leads processed
- hot replies detected
- dashboard check frequency

## 15. Pricing Hypothesis
### Service-first
- setup fee
- monthly management fee

### Productized later
- subscription + usage or seats
- premium for multi-location
- premium for advanced call / SMS automation

## 16. MVP Delivery Model
### Step 1
- install on one business manually and measure outcomes

### Step 2
- convert recurring setup into templates

### Step 3
- move repeated parts into software

## 17. Risks
- SMS/call compliance
- low-quality lead data
- integration fragility
- business owners not responding quickly enough
- over-automation causing bad customer experience

## 18. Mitigations
- opt-in and compliance rules
- manual review on critical messages
- pause/override controls
- simple fallback workflows
- tight logging

## 19. 30-Day Execution Plan
### Week 1
- finalize niche and offer
- build demo
- create lead list
- write sequences

### Week 2
- start outreach
- book pilots
- install first account

### Week 3
- refine sequences from real replies
- measure revenue signals
- install additional pilots

### Week 4
- close paid client
- package templates
- document reusable setup

## 20. Definition of Done for v1
The product is done when it can:
- capture leads
- follow up automatically
- recover missed opportunities
- request reviews
- show results in a simple dashboard
- be installed again with mostly reusable templates

## 21. Future Roadmap
- multi-location support
- call intelligence
- website chat intake
- AI-assisted quoting
- deeper CRM sync
- vertical expansions to HVAC, roofing, med spa, plumbing

## 22. Open Questions
- Which pest-control sub-niche should be first?
- What SMS/calling stack should be used?
- Which CRM is easiest to integrate first?
- What is the minimum dashboard that still shows ROI?
