# Pest Control Revenue Infrastructure, MVP v1

## Goal
Ship the smallest installable version that recovers revenue from missed calls, web leads, quotes, and stale customers.

## MVP Promise
Increase booked jobs by making follow-up automatic, visible, and hard to forget.

## Scope, Must Have
1. Missed-call text back
2. Web lead capture
3. Quote follow-up sequence
4. Review request sequence
5. Dormant lead reactivation
6. Simple dashboard
7. Logging for every touchpoint
8. Manual edit / pause / override

## Explicitly Out of Scope
- full CRM replacement
- advanced analytics
- multi-industry platform
- custom mobile app
- deep dialer stack
- accounting / invoicing

## Install Inputs Required
- business name
- service areas
- phone number(s)
- lead source paths
- review link
- quote follow-up timing
- owner or dispatcher contact
- existing lead CSV if available

## Setup Flow
1. Collect business data
2. Configure lead intake
3. Load templates
4. Turn on missed-call recovery
5. Turn on quote follow-up
6. Turn on review requests
7. Import old leads
8. Verify dashboard and logs

## Core Sequences
### Missed call
- reply within minutes
- ask for name, address, issue, preferred time
- notify office

### Quote follow-up
- day 0, immediate reminder
- day 2, gentle follow-up
- day 5, urgency check
- day 10, final nudge

### Review request
- send after job complete
- include review link
- stop if review received or owner pauses

### Reactivation
- send to stale leads and old customers
- offer quote refresh or inspection
- surface replies to owner

## Dashboard v1
Show:
- new leads
- unanswered leads
- replied leads
- booked jobs
- quote follow-up status
- review request sent
- reactivation responses
- last system activity

## Success Criteria
- missed calls are replied to automatically
- follow-up sequences run without manual babysitting
- owner can see revenue opportunities at a glance
- first pilot can be installed again with minimal changes

## Pilot Deliverable
- working follow-up system
- editable message templates
- basic dashboard
- log of actions
- short weekly ROI summary

## First Revenue Angle
- setup fee for install
- monthly fee for management
- optional performance bonus tied to booked jobs or recovered leads
