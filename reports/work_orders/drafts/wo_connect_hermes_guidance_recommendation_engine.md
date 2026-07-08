# Work Order: Connect Hermes Guidance to Real Recommendation Engine

**Status:** Draft
**Priority:** Medium
**Source:** Client Portal Premium UI Foundation Sprint
**Created:** 2026-07-07

## Objective
Replace static Hermes guidance text with dynamic recommendations from the recommendation engine.

## Scope
- Query `recommendations` table for client-specific suggestions
- Use `recommendation_engine.py` scoring for priority ordering
- Update Hermes panel per page context (credit, documents, business, funding)
- Show real next actions based on actual client state

## Acceptance Criteria
- Hermes guidance updates dynamically based on client data
- Recommendations scored and ranked by the engine
- Guidance reflects actual missing items, not hardcoded text
- Advisory disclaimer preserved

## Dependencies
- Recommendation engine must be operational
- Client profile data must be available
- `recommendations` table must have `client_id` and `context_type` columns
