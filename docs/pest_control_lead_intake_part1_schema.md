# Lead Intake Part 1, Spreadsheet Schema

## Raw Input Columns
- raw_name
- raw_email
- raw_website
- raw_company
- raw_phone
- raw_notes
- raw_source

## Normalized Columns
- lead_id
- name
- email
- website
- company
- phone
- source
- confidence
- status
- duplicate_of
- opt_out
- review_flag
- error_reason
- retry_count
- last_updated

## Diagnostics Columns
- step_name
- step_status
- step_error
- manual_action_needed
- last_attempted_at

## Status Values
- new
- queued
- normalized
- error
- skipped

## Rules
- never overwrite raw fields
- write normalized fields separately
- preserve duplicate links
- keep a row-level audit trail
- no outbound actions in Part 1
