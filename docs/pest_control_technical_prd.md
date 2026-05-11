# Pest Control Revenue Infrastructure, Technical PRD

## 1. Purpose
Define the technical system that executes revenue recovery workflows for pest control companies.

## 2. System Goals
- recover missed leads
- automate follow-up
- increase booked jobs
- request reviews
- surface revenue leakage
- remain installable for new clients with repeatable templates

## 3. Architecture Style
Event-driven workflow system.

### Layers
- intake
- orchestration
- AI assist
- rules engine
- action execution
- data storage
- monitoring

## 4. Core Components
### 4.1 Intake Service
Responsibilities:
- receive missed-call events
- receive web lead submissions
- accept CSV imports
- accept manual lead creation
- receive job completion events for reviews

### 4.2 Orchestrator
Responsibilities:
- choose workflow path
- start sequences
- stop sequences when a lead responds or books
- route exceptions to humans
- enforce idempotency

### 4.3 AI Assist
Responsibilities:
- classify lead intent
- suggest next action
- draft replies
- summarize conversations
- score lead quality

### 4.4 Rules Engine
Responsibilities:
- timing of messages
- stop conditions
- escalation rules
- business hours rules
- compliance rules

### 4.5 Action Layer
Integrations:
- SMS / calling provider
- Gmail
- CRM
- Google Sheets
- Google Drive
- notifications
- dashboard updates

### 4.6 Data Store
Entities:
- Lead
- Event
- Conversation
- Sequence
- SequenceStep
- Outcome
- ReviewRequest
- AuditLog

### 4.7 Monitoring
Responsibilities:
- log all actions
- track failed sends
- track reply rates
- track bookings
- track reviews requested and received
- show revenue recovered

## 5. Key Workflows
### 5.1 Missed Call Recovery
Trigger: missed call
Flow:
- create event
- send text back
- classify reply
- notify owner if hot
- continue follow-up if no reply
- log outcome

### 5.2 Quote Follow-Up
Trigger: quote sent
Flow:
- start timed reminders
- stop on reply/booked
- notify owner on hot response

### 5.3 Review Request
Trigger: job completed
Flow:
- send review request
- stop on successful review or manual pause
- log result

### 5.4 Dormant Lead Reactivation
Trigger: imported stale leads
Flow:
- send reactivation sequence
- classify replies
- route hot leads to owner

## 6. Non-Functional Requirements
- high reliability
- simple manual override
- low setup overhead
- clear logging
- traceable actions
- compliance-aware messaging
- minimal dependency sprawl in MVP

## 7. Failure Handling
If a step fails:
- log failure
- retry if safe
- alert owner or operator
- pause sequence if needed
- preserve state for resume

## 8. MVP Stack
- Google Sheets for operational data
- Gmail for outreach
- SMS/calling provider for lead contact
- n8n or Zapier for automation
- LLM API for drafting and classification
- simple dashboard for visibility

## 9. Extensibility
Later add:
- multi-location support
- CRM sync
- call transcription
- lead scoring model
- performance analytics
- broader vertical templates

## 10. Definition of Done
The system is done when it can:
- ingest leads
- trigger workflows
- automate follow-up
- recover opportunities
- request reviews
- log outcomes
- be installed again using templates
