# Nexus Supabase Profile and Storage Audit — 2026-09-27

Project: `iqjwgpnujbeoyaeuwehj` (`nexus-os-v2`)

## Method

Schema metadata, `pg_policies`, and the Storage bucket registry were queried
through the existing authenticated Supabase management access. No row values,
file listings, credentials, or customer data were retrieved. No database or
storage mutation was performed.

## Actual schema

`public.client_profiles` exists and contains the profile-intake columns used by
the current client adapter: `legal_name`, `preferred_name`, `phone`, mailing
address fields, `business_name`, `entity_type`, `ein_status`, `industry`,
`naics_code`, business address fields, `time_in_business`,
`monthly_revenue_range`, and `funding_goal_range`. It has no `avatar_path`,
`avatar_url`, `business_logo_path`, or `business_logo_url` column.

`public.business_profile_requirements` exists as the workflow/guidance table;
it is not a separate personal/business profile table and does not provide media
storage fields.

No client-facing settings or preferences table was found. A generic `public.settings`
table exists with `key`, `value`, and `updated_at`, but its actual RLS is admin
read-only and it is not a client preference store.

## Actual Storage

The bucket registry contains:

- `client-documents` — private, 10 MiB limit, PDF/JPEG/PNG/HEIC/TXT/DOCX types.
- `creative-assets` — private, no configured MIME/size restriction shown.
- `goclear-approved-media` — public, MP4-only, 50 MiB limit.

There is no avatar, profile, client-media, client-assets, business-logo, logos,
images, or general client media bucket. `client-documents` has authenticated
client upload/read policies based on the first path segment matching `auth.uid()`;
there is no client replace/update policy in the discovered object policies.

## RLS

`client_profiles` has self-select and self-update policies scoped through
`tenant_memberships.tenant_id`, `tenant_memberships.client_id`, and
`auth.uid()`, plus separately governed admin/operator policies. This preserves
tenant/client isolation. The generic `settings` table has an admin-read policy,
not client write access. Storage policies only cover private client documents.

Therefore:

- own avatar upload/read/replace: not supported (no bucket/column/policies)
- own business-logo upload/read/replace: not supported (no bucket/column/policies)
- existing document upload/read: supported by the existing private document path

## Code comparison and decision

The current Profile UI correctly treats avatar and business-logo upload as
unavailable and the adapter uses the canonical `client_profiles` intake fields.
Its document-only storage assumption matches the real bucket registry. No
existing capability was missed by the code audit. No safe storage addition or
schema addition is required for this audit, and none was made.

`DATABASE_MUTATIONS_PERFORMED=NO`, `RLS_WEAKENED=NO`, `CLIENT_DATA_EXPOSED=NO`.
