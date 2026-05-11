# Lead Intake Part 1, Diagnostics Backlog

## Track These Issues
- missing email
- invalid email
- invalid website
- duplicate lead
- uncertain duplicate
- low confidence record
- missing company name
- missing phone
- conflicting company names
- retry failure
- write-back failure
- unexpected status transition

## Required Fields in Diagnostics
- lead_id
- row_id
- step_name
- step_status
- step_error
- retry_count
- manual_action_needed
- last_attempted_at
- last_updated

## Backlog Priority
1. failures that block processing
2. duplicates
3. low-confidence records
4. missing optional enrichment
5. reporting gaps
