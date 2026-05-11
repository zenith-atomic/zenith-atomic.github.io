# Pest Control Revenue Infrastructure, Box-and-Arrow Architecture

## Overview
This is an event-driven system for recovering revenue from missed calls, web leads, stale quotes, and old customers.

## Box and Arrow

[Lead Sources]
- missed calls
- web forms
- CSV imports
- old lead lists
- completed jobs
        |
        v
[Event Intake]
- normalize incoming data
- create a lead event
- assign source and type
        |
        v
[Workflow Orchestrator]
- decides next action
- starts sequences
- stops on reply/booked
- routes human exceptions
        |
        +--------------------+
        |                    |
        v                    v
[AI Assist Layer]      [Rules Engine]
- classify intent      - timing rules
- draft replies        - stop rules
- summarize threads    - escalation rules
- score leads          - routing rules
        |                    |
        +---------+----------+
                  v
            [Action Layer]
- SMS
- calling
- Gmail
- CRM
- Sheets
- notifications
                  |
                  v
            [Data Layer]
- leads
- conversations
- sequences
- outcomes
- review requests
- audit logs
                  |
                  v
          [Monitoring / Reporting]
- what ran
- what failed
- what booked
- what needs human help
- revenue recovered

## Typical Flow
1. missed call comes in
2. event is created
3. workflow sends text back
4. AI classifies response
5. rules engine decides whether to continue or stop
6. action layer sends follow-ups
7. data layer logs everything
8. monitoring surfaces wins and failures

## Design Principle
Workflow first, AI assisted, human override always available.
