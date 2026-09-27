# Nexus Client Business Presence Profile — 2026-09-27

## Scope

The existing `public.client_profiles` table was audited in Supabase project
`iqjwgpnujbeoyaeuwehj`. The requested business-presence fields were absent. A
single safe additive migration added them to that table; no duplicate profile
table, storage bucket, RLS policy, or sensitive identity field was created.

## Added fields

Business contact: `business_website`, `business_phone`, `business_email`, and
`formation_date`.

Google Business Profile: `google_business_profile_status` and
`google_business_profile_url`.

Optional social presence: `linkedin_business_url`, `facebook_business_url`,
`instagram_business_url`, `youtube_channel_url`, and
`other_business_social_url`.

Verification state: address, website, phone, email, and Google Business Profile
verification-status columns, defaulting to `UNKNOWN`. These are informational
identity/presence states and are not funding approval decisions.

## Client Portal

The canonical Profile page now reads and saves the new fields through the same
tenant-scoped `client_profiles` adapter. A compact Business Contact & Digital
Presence section uses the existing Tailwind 4 field/card/button language. The
desktop contact section uses a denser three-column field grid; mobile remains a
single-column flow. Social fields are optional and excluded from the required
profile-completeness contract.

The existing onboarding completion semantics were preserved. The Profile page
can show business address, phone, email, and website as missing for its fuller
profile view without changing authentication or onboarding redirects.

## Storage and governance

The existing private `client-documents` bucket remains unchanged. No avatar or
business-logo bucket was created because the prior audit found no safe canonical
media contract and this task did not require forcing media infrastructure.

RLS and tenant isolation were preserved by using the existing table policies.
No client data was exported or mutated for testing. No customer-facing,
financial, paid, publication, or trading action was performed.
