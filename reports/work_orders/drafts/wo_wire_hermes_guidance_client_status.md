# Work Order: Wire Hermes Guidance to Client Status

**Status:** Draft
**Priority:** Medium
**Created:** 2026-07-07

## Goal
Replace static mock guidance with dynamic guidance based on real client status.

## Why It Matters
Clients need personalized guidance based on their actual progress, not hardcoded demo text.

## Scope
- Use `clientGuidance.ts` generator (created in this sprint)
- Query `approved_client_guidance` table for admin-approved guidance
- Fall back to generator when no approved guidance exists
- Update `HermesGuidancePanel` to use dynamic data

## Acceptance Criteria
- Guidance updates based on client's actual status
- Missing documents trigger relevant guidance
- High utilization triggers credit guidance
- Admin-approved guidance takes precedence
- No external API calls required

## Files Involved
- `src/clientPortal/clientGuidance.ts` (created)
- `src/components/client/ClientPortalShell.jsx` (update HermesGuidancePanel)
- `src/clientPortal/useClientPortalData.ts` (pass status to generator)

## Risk Level
Low — client-side only, no external calls

## Test Plan
1. Test with mock data (fallback to static)
2. Test with partial Supabase data
3. Verify guidance changes based on status
