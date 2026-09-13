# R29.1 Client Portal V2 Adapter Matrix

This is the engineering contract for the isolated `/client-v2` route family.
It is intentionally design-neutral. Final visual composition remains subject
to the R30A visual-design gate.

All routes receive the authenticated, tenant-scoped `V2ViewData` produced by
`useV2ClientData`. Contract-only routes additionally resolve a named adapter
through `resolveRouteAdapter`; this prevents a route from silently becoming a
mock or falling back to the legacy portal.

| Route | Adapter boundary | Backend/source | State | Legacy fallback |
| --- | --- | --- | --- | --- |
| `/client-v2/dashboard` | `DashboardV2` | Supabase client context/readiness adapter | live/loading/error/empty | no |
| `/client-v2/credit` | `creditRepair + scores` | Supabase client-scoped credit/readiness data | live/loading/error/empty | no |
| `/client-v2/utilization` | `profile + credit data` | Supabase client profile/readiness data | live/loading/error/empty | no |
| `/client-v2/documents` | `DocumentsV2` | Supabase document/storage/RLS adapter | live/loading/error/empty | no |
| `/client-v2/business` | `flow + readiness` | Supabase business/readiness data | live/loading/error/empty | no |
| `/client-v2/bankability` | `readiness + documents` | Supabase bankability/document data | live/loading/error/empty | no |
| `/client-v2/funding-readiness` | `FundingReadinessV2` | Supabase readiness + governed funding gate | live/loading/error/empty | no |
| `/client-v2/recommendations` | `Hermes approved recommendations` | approved, tenant-scoped client guidance | live/loading/error/empty | no |
| `/client-v2/resources` | `approved resource boundary` | approved GoClear knowledge source | live/loading/error/empty | no |
| `/client-v2/review` | `flow.reviewStatus` | Supabase review/case state | live/loading/error/empty | no |
| `/client-v2/support` | `customer_service` gateway | Supabase-backed Customer Service path | live/loading/error/empty | no |
| `/client-v2/account` | `profile + auth context` | Supabase Auth/client profile | live/loading/error/empty | no |

The matrix covers read-state binding. Mutations remain governed by the
existing backend contracts and are exposed only by pages that have an approved
action composition. No payment, publication, internal-state, or cross-tenant
authority is implied by this read adapter layer.

## Design-gated screens

`CLIENT_DASHBOARD`, `DOCUMENTS`, `FUNDING_READINESS`, `CLYDE_MOBILE`, and
`CLIENT_MOBILE_NAVIGATION` remain `VISUAL_DESIGN_PENDING=YES`. Their backend,
auth, tenant, and state contracts are ready for an approved visual reference.
