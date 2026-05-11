# Status Monitor Dashboard Spec

## Purpose
Give a quick view of what each project and agent is doing, what is blocked, and what needs review.

## Top-Level Fields
- project_name
- project_type
- current_phase
- owner
- priority
- last_updated
- next_action
- status

## Agent Fields
- agent_name
- agent_role
- current_task
- task_status
- output_link
- blocker
- retry_count
- last_run

## Project Fields
- summary
- backlog
- active_tasks
- completed_tasks
- open_issues
- new_additions
- risks
- approvals_needed

## Dashboard Views
### Project view
Shows the current state of one project.

### Agent view
Shows what each agent is doing and whether it needs review.

### Backlog view
Shows outstanding tasks, blockers, and next actions.

### Change feed
Shows what changed since the last review.

## Update Rules
- update after every meaningful task
- surface new additions immediately
- flag blockers prominently
- separate done from pending
- keep the dashboard short and scannable

## Success Criteria
- you can tell at a glance what is happening
- you can see what changed
- you can see what needs review
- you can spot blockers quickly
