# Nexus Client Portal Integration Bridge

This directory is an integration boundary for the approved Google AI Studio portal design.

## Design lock

The bridge is intentionally separate from the visual components. Integrating Nexus data must not require changing:
- typography
- icons
- card dimensions
- spacing
- colors
- borders/shadows
- readiness journey layout
- overdue/blocked visual states
- Clyde placement
- navigation density

## Runtime contract

The prototype remains fully functional in demo mode when no bridge is injected.

The Nexus host application can inject `window.__NEXUS_CLIENT_PORTAL_BRIDGE__` before React mounts.

If no bridge is present, the original design data remains the demo/preview fallback.

## Intended Nexus mappings

- `profile` → authenticated client / tenant profile
- `journeyNodes` → readiness workflow status
- `missions` → readiness actions / blockers
- `documents` → Supabase document metadata + storage state
- `bankabilityPillars` → current bankability engine
- `setupSteps` → entity / business-readiness state
- `recommendations` → Nexus/Alpha/Clyde recommendations
- `resources` → curated resources
- `sendClydeQuery` → Clyde backend
- `requestUnderwritingReview` → governed review workflow
- `uploadDocument` → tenant-scoped storage workflow

No Supabase credentials or privileged service-role keys belong in this frontend.
