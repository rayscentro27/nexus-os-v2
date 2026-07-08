# Work Order: Build Business Funding Readiness Workflow Data Model

**Status:** Draft
**Priority:** Medium
**Source:** Client Portal Premium UI Foundation Sprint
**Created:** 2026-07-07

## Objective
Create a structured data model for business funding readiness tracking.

## Scope
- `funding_readiness_scores` table: factor scores, overall readiness, timestamps
- `funding_blockers` table: identified blockers, resolution status
- `funding_actions` table: recommended actions, completion status
- `funding_applications` table: application tracking (when approved)

## Acceptance Criteria
- Readiness scores stored per client with history
- Blockers tracked with resolution status
- Actions tracked with completion status
- Client portal shows real readiness scores instead of demo data
- Funding range estimate reflects actual readiness level

## Dependencies
- Credit profile data model must be in place
- Business setup data model must be in place
- GoClear review workflow must define approval gates
