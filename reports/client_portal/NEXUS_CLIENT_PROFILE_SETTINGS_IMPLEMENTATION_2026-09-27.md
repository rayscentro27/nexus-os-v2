# Client Profile and Settings Implementation

Date: 2026-09-27

## Outcome

Added authenticated `/client/profile` and `/client/settings` experiences
through the existing approved GoClear Ascent Tailwind 4 portal shell. The
existing command center, journey, mission grid, Clyde UI, footer, navigation
visual language, login, and existing client surfaces were not redesigned.

Canonical routes are `/client-v2/profile` and `/client-v2/settings`; the
existing `/client/profile` and `/client/settings` aliases map to them.

## Data and storage audit

- Existing client profile storage: tenant-scoped `public.client_profiles`,
  accessed through `loadClientProfileIntake` and `saveClientProfileIntake`.
- Existing business profile storage: the same `client_profiles` intake columns,
  plus existing `business_profile_requirements` read data.
- Existing avatar storage: no profile-avatar storage contract. The portal's
  private `client-documents` bucket is for document uploads only.
- Existing business-logo storage: no approved client-facing field or bucket
  contract.
- Existing supported fields reused: legal name, preferred name, phone, mailing
  address, business name, entity type, EIN status, industry, NAICS code,
  business address, time in business, revenue range, and funding goal range.
- Missing schema fields intentionally not invented: auth email is read-only
  from Supabase Auth; website, distinct business phone, formation date,
  profile photo, business logo, and communication-preference storage are not
  silently added.

Profile completeness is derived from the saved intake fields through the
existing `checkProfileIntakeComplete` / `profileCompleteness` logic. It is
informational and does not alter readiness scores.

## Auth and tenant safety

Authentication semantics are unchanged. Profile loading and saving continue to
resolve the authenticated client context and use the existing client profile
adapter/RLS boundary. Password reset uses the existing Supabase Auth reset
flow. No SSN or full EIN field was added.

Photo and logo upload controls are truthful unavailable states. No public
bucket, unrestricted upload, or duplicate profile table was created.

## Visual implementation

The new pages use the approved portal's existing Tailwind 4 output, typography,
colors, radii, borders, shadows, form controls, and button language. The
profile view uses an identity/completeness card plus compact personal and
business sections. Settings uses compact account, profile, security, and
truthful unsupported-preferences sections. Mobile collapses to one column.

Navigation access is added to the existing avatar menu without changing the
main journey ordering or sidebar treatment.

## Tests

- `npm run typecheck`: PASS
- `npm run build`: PASS
- focused Vitest profile/settings route and safety tests: 2 passed
- existing approved portal Playwright visual parity: desktop and mobile passed
- `git diff --check`: PASS

The Playwright smoke used the installed system Google Chrome executable because
the bundled Playwright Chromium download is unsupported on this macOS 12 host.
