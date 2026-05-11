# Pest Control Lead Intake, Part 1

## Purpose
Create a clean, reliable lead intake queue that normalizes spreadsheet rows before any research, drafting, or outreach.

## Input
Each lead starts as a row with:
- name
- email
- website
- optional company
- optional phone
- optional notes

## Output
A normalized lead record with:
- lead_id
- status
- name
- email
- website
- company
- phone
- source
- confidence
- duplicate_of
- opt_out
- review_flag
- error_reason
- retry_count
- last_updated

## Statuses
- new
- queued
- normalized
- researching
- drafted
- reviewed
- approved
- sent
- error
- skipped

## Rules
### Validation
- email must be present and valid
- name should be present if possible
- website should be captured if available

### Dedupe
- do not process the same lead twice
- if company and website match a prior record, link to duplicate_of
- if the email matches an existing record, skip or merge based on rules

### Compliance
- respect opt-out flags
- never send if opt_out is true
- do not auto-send leads marked for review

### Review flags
Flag for human review if:
- email is missing
- website is invalid
- duplicate is uncertain
- company name conflicts
- confidence is low

## Processing Flow
1. read one spreadsheet row
2. validate required fields
3. assign lead_id
4. detect duplicates
5. set status
6. set confidence
7. write record back
8. log errors if any

## Error Handling
- missing email -> error
- invalid email -> error
- missing website -> allow but reduce confidence
- duplicate -> skip or merge
- agent failure -> retry once, then error

## Diagnostics
Store:
- step_name
- error_reason
- retry_count
- timestamp
- row_id
- manual_action_needed

## Smoke Test
Use one sample row and confirm:
- it loads
- validation runs
- duplicate logic works
- status writes back
- errors are recorded

## Definition of Done
Part 1 is done when a spreadsheet row can be turned into a stable normalized lead record with status, dedupe, validation, and diagnostics, without sending anything.
