# Nexus UI Connection Matrix

Date: 2026-06-24

## Connection Chain

| Layer | Status | Evidence | Smallest repair |
|---|---|---|---|
| Netlify deployed bundle | Latest bundle likely deployed | Public JS contains Supabase session persistence fix and correct project ref | Deploy current diagnostic build after commit |
| Browser cache/service worker | Not likely | No service worker/PWA registration found; `/sw.js` is not a real service worker | Hard refresh/incognito only to reset browser auth/session state |
| Frontend env vars | Likely configured for Supabase | Deployed bundle contains Supabase project ref `iqjwgpnujbeoyaeuwehj` | Add missing-env diagnostics in UI |
| Supabase client | Configured if VITE URL/key are present | `src/lib/supabaseClient.ts` uses anon key only | Keep service role out of frontend |
| Auth session | Unknown in Ray's browser | Cannot inspect Ray's local browser session remotely | Show session status in UI |
| Admin mapping | Backend row exists | Active admin row exists for `goclearonline@gmail.com`; policies use `admin_users.id = auth.uid()` | Show user email/id prefix and admin lookup status |
| RLS | Valid but admin-gated | Migrations gate reads through active admin row | Do not weaken; surface denial clearly |
| Frontend queries | Previously opaque | Generic reads returned `[]` on errors | Return safe query diagnostics |
| UI rendering | Previously misleading | Empty state could mean no data or failure | Render status/error panels |

## Tab Matrix

| Tab | Component/file | Data source | Auth/admin required | Current behavior after fix | Status | Smallest repair |
|---|---|---|---|---|---|---|
| Command Center | `CommandCenter`, `src/components/sections.tsx` | Hermes chat edge function, safe reports, `task_requests`, awareness counts | Auth for dashboard shell; admin for awareness table reads | Chat works; awareness counts use Supabase reads | Live, partially dependent on admin reads | Show awareness read errors if needed |
| System Health | `SystemHealth`, `src/components/sections.tsx` | `system_health` | Admin required by RLS | Shows connection status or health cards | Live with diagnostics | Seed/refresh health rows if empty |
| Agent Jobs | `AgentJobsView`, `src/components/sections.tsx` | `agent_registry`, `agent_jobs` | Admin required by RLS | Shows runner commands and diagnostic status for registry/jobs | Live with diagnostics | Add one-click safe job status refresh later |
| Approvals | `ApprovalCenter`, `src/components/sections.tsx` | `approvals`, `admin_users` diagnostic | Admin required by RLS | Shows full Supabase/auth/admin/query panel | Live with diagnostics | Deploy and confirm Ray's signed-in user matches admin row |
| GoClear / Apex | `GoClearWorkspace`, `src/components/sections.tsx` | `partner_offers`, `client_recommendations` | Admin required by RLS | Shows status for no records/query errors | Live foundation, likely sparse | Seed/update offers and recommendations |
| Opportunity Lab | `OpportunityLab`, `src/components/sections.tsx` | `monetization_opportunities` | Admin required by RLS | Shows status for no records/query errors | Live/report-fed | Connect watch loop opportunities to UI |
| Intake & Orientation | `IntakeOrientation`, `src/components/sections.tsx` | `transcript_reviews`, `orientation_notes`, `intake_events` | Admin required by RLS | Shows status for no records/query errors | Live/manual runner | Add safe capture form later |
| Creative Studio | `CreativeStudio`, `src/components/sections.tsx` | `creative_campaigns`, briefs, assets, scores, design/publish tables | Admin required by RLS | Shows status for no records/query errors; queue buttons create jobs only | Working manually with approvals | Run safe creative jobs and surface latest package |
| Design Library | `DesignLibrary`, `src/components/sections.tsx` | design inspiration/pattern/packet/review tables | Admin required by RLS | Shows status for no records/query errors | Live/scaffolded | Add latest design packet summary |
| Trading Lab | `TradingLab`, `src/components/sections.tsx` | `trading_strategy_candidates`, `trading_risk_rules` | Admin required by RLS | Shows status for no records/query errors | Report-only/demo-safe | Add Oanda demo connection proof rows |
| SEO / Marketing | `SeoOs`, `src/components/sections.tsx` | `seo_sites`, `seo_opportunities` | Admin required by RLS | Shows status for no records/query errors | Registered/scaffolded | Seed first GoClear SEO opportunity |
| Model Router | `ModelRouter`, `src/components/sections.tsx` | `model_providers`, `model_routes`, `model_route_decisions`, `hermes_model_requests` | Admin required by RLS | Shows diagnostics for providers/routes/requests | Live policy view | Add route-decision proof for Hermes requests |
| Integrations | `Integrations`, `src/components/sections.tsx` | `integration_registry` | Admin required by RLS | Shows status for no records/query errors | Registered/report-only | Add connection test status per integration |
| Ops & Improvements | `OpsImprovements`, `src/components/sections.tsx` | `ops_incidents`, `improvement_candidates` | Admin required by RLS | Shows status for no records/query errors | Live/report-fed | Convert blockers into improvement candidates |
| Events Feed | `EventsFeed`, `src/components/sections.tsx` | `nexus_events` | Admin required by RLS | Shows status for no records/query errors | Live proof log | Add filters by lane/status |

## Expected Approval Visibility

Approval `13eafcab-6940-4612-8239-54786e8c9e60` should appear if:

- Netlify has the current diagnostic build.
- Supabase env vars point at project `iqjwgpnujbeoyaeuwehj`.
- Ray is signed in.
- The signed-in auth user id equals an active row in `admin_users`.
- RLS policies are unchanged.

If any condition fails, the Approvals diagnostic panel should identify the failed layer.
