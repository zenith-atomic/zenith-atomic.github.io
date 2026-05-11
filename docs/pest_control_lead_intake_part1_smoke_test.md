# Lead Intake Part 1, Smoke Test

## Goal
Verify that a spreadsheet row becomes a normalized lead record with correct status, dedupe, validation, and diagnostics.

## Test Case 1, Valid Lead
### Input
- name: Mike Adams
- email: mike@example.com
- website: https://examplepest.com
- company: Example Pest Control
- phone: 555-111-2222
- notes: sample row

### Expected
- lead_id assigned
- status = normalized
- confidence = high
- duplicate_of = empty
- review_flag = false
- error_reason = empty
- diagnostics logged

## Test Case 2, Missing Email
### Input
- name: Sarah Lee
- email: empty
- website: https://examplepest.com
- company: Example Pest Control

### Expected
- status = error
- error_reason = missing email
- review_flag = true
- diagnostics logged
- no outbound action

## Test Case 3, Duplicate Company + Website
### Input
- name: Mike Adams
- email: mike.alt@example.com
- website: https://examplepest.com
- company: Example Pest Control

### Expected
- duplicate_of populated if prior record exists
- status = skipped or normalized per rule
- review_flag set if duplicate is uncertain
- diagnostics logged

## Test Case 4, Invalid Website
### Input
- name: Erin Jones
- email: erin@example.com
- website: not-a-url
- company: Example Pest Control

### Expected
- status = error or normalized with low confidence depending on rule
- error_reason notes invalid website
- review_flag = true
- diagnostics logged

## Pass Criteria
- rows are processed one at a time
- status updates correctly
- errors are recorded
- duplicates are detected
- no sending occurs

## Fail Criteria
- missing fields are ignored
- duplicates are processed twice
- errors are not logged
- outbound action is triggered
