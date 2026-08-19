# GoClear First-Experience Audit — Phase 16A

## Verdict

`PARTIAL — operational safety repair started; first-login/onboarding and branded Auth email remain unproven.`

The existing client-v2 architecture is reusable, but the current implementation does not yet prove a clean real client’s first experience. The older audit scored the portal 35/100 and identified mock data, weak hierarchy, unclear CTAs, and weak mobile behavior.

## Current flow

`signup → Supabase confirmation → ClientLoginPage → /client/dashboard or /client-v2 → live adapter/demo fallback`

The login page provides GoClear copy and support contact, but redirects directly to a dashboard. `ClientV2Root` checks client access but does not read a canonical onboarding-complete state. The repository does not contain the Supabase Auth email-template configuration.

## Safety finding repaired

Several live Supabase list readers returned seeded synthetic tasks or readiness scores when a real client query returned zero rows. That could make a clean client appear to have progress. The live adapter now preserves successful empty Supabase results as empty results. The default preview remains explicitly synthetic and is not a real-client surface.

## Design assessment

- Trust: `PARTIAL` — GoClear identity/support copy exists; first-run proof is missing.
- Clarity: `PARTIAL` — v2 has a journey rail and next-action card, but onboarding routing is not enforced.
- Empty states: `REPAIR_IN_PROGRESS` — adapter fallbacks were unsafe for live mode; browser proof remains required.
- Typography/spacing/mobile: `PARTIAL` — existing v2 design system is a usable base, not certification.
- CTA clarity: `PARTIAL` — action components exist; first-login CTA is not yet state-driven.

## Hard blockers

1. Add or verify a canonical `onboarding_complete`/journey-state read and route first login to onboarding.
2. Configure and verify branded Supabase confirmation, reset, invitation, and email-change templates.
3. Run a browser proof against a clean authenticated test account with live mode enabled.
4. Ray must select a design territory before a broad visual direction is promoted.

No external client was onboarded and no production Stripe behavior was changed.
