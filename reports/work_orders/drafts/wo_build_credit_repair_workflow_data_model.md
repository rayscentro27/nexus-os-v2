# Work Order: Build Credit Repair Workflow Data Model

**Status:** Draft
**Priority:** Medium
**Source:** Client Portal Premium UI Foundation Sprint
**Created:** 2026-07-07

## Objective
Create a structured data model for credit repair workflow tracking.

## Scope
- `credit_repair_cases` table: dispute status, bureau, account, result
- `credit_dispute_letters` table: letter templates, send status, response tracking
- `credit_score_history` table: score snapshots over time
- Client portal integration: show dispute status, score trends, next actions

## Acceptance Criteria
- Dispute cases tracked with status (draft → sent → responded → resolved)
- Score history stored with bureau, score, date
- Client portal shows real dispute status instead of demo data
- Hermes guidance reflects actual credit repair progress

## Dependencies
- Credit monitoring integration (optional)
- GoClear review workflow alignment
