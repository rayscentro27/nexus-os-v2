## Superseding live remediation result — 2026-10-09

**OBSERVED FACT:** The earlier sections below record pre-remediation discovery and are superseded for current behavior by `reports/remediation/NEXUS_SUPABASE_REMEDIATION_20261009.md`. The live upload trigger now enqueues one governed durable credit job and no longer creates a legacy credit queue row. Seven provider-action Edge endpoints are deployed fail-closed; all 10 Supabase provider callsites are disabled. Live tests, rollback-only canary, migration results, source parity, and remaining intentional drift are documented in the remediation report.

**DECISION:** `SUPABASE_BLOCKER_CLASS=SAFE_FOR_STAGED_ACTIVATION`; `CORE_TRACK_B_ACTIVATION_READY=YES`. This does not close the global pre-activation gate or authorize runtime activation.

# NEXUS SUPABASE LIVE CONTROL-PLANE CLOSURE

Observed 2026-10-09. Project: `iqjwgpnujbeoyaeuwehj` (`nexus-os-v2`).

## Result

- **OBSERVED FACT:** Safe mode remained active. No scheduler, dispatcher, legacy kernel, active operator, certification, function deployment, provider invocation, database mutation, or job execution occurred during this pass.
- **OBSERVED FACT:** The authenticated Supabase CLI and linked read-only SQL path are usable. CLI version is 2.90.0; the project is linked and reported `ACTIVE_HEALTHY`. Project ref matches the expected value.
- **OBSERVED FACT:** Live catalog access succeeded as database role `postgres`. The project has 87 remote migration records versus 88 timestamped local migration files. Local-only migration: `20261021160000_nexus_telegram_governor_default_deny.sql`; no remote-only migration was found.
- **OBSERVED FACT:** A read-only Supabase Management API request using the locally stored CLI Keychain credential returned HTTP 401 for both Auth config and project webhook endpoints. Values were not emitted. SQL/CLI evidence is still sufficient to inventory database automation and deployed Edge Function metadata, but not account-level Auth hooks or project webhook registrations.
- **RECOMMENDATION:** Do not activate Nexus. The specific live blockers are the legacy event-driven credit queue and active ungoverned Edge provider callers. Auth-hook/project-webhook admin metadata also remains inaccessible.

## Live PostgreSQL automation

| Inventory | Live result |
|---|---|
| Installed extensions | `pg_stat_statements`, `pgcrypto`, `plpgsql`, `supabase_vault`, `uuid-ossp` |
| `pg_cron` / `cron` schema | Absent; `SUPABASE_CRON_JOBS=0` |
| `pg_net` / `net` schema | Absent |
| `supabase_functions` schema | Absent |
| Non-internal database triggers | 18, all enabled in ORIGIN mode |
| Event triggers | 6, Supabase/PostgREST/GraphQL DDL and drop handlers |
| Security-definer functions | 20 |
| Network-marked functions | One grant helper, `extensions.grant_pg_net_access`; no installed `pg_net` and no live SQL HTTP caller found |
| Database HTTP/webhook triggers | 0 identified |

- **OBSERVED FACT:** No `pg_cron` extension, cron schema, `pg_net` extension, `net` schema, or `supabase_functions` schema is installed. The live database has no recurring database schedule and no active database HTTP/webhook mechanism in the inspected catalog.
- **OBSERVED FACT:** The six event triggers are platform catalog maintenance handlers. No event trigger references Nexus work tables or provider/network calls.
- **OBSERVED FACT:** `public.nexus_schedule_durable_jobs()` is security-definer and writes durable jobs, but EXECUTE is granted to `service_role` only. No database trigger or cron job invokes it. It is a callable scheduler-side function, not a database-owned scheduler.

## Credit-report trigger

- **OBSERVED FACT:** `public.queue_credit_report_after_upload()` is attached to `public.client_documents` by enabled trigger `queue_credit_report_after_upload_trigger`.
- **OBSERVED FACT:** The function is security-definer, uses `auth.uid()`, and inserts into `credit_analysis_jobs`, `credit_document_workflows`, and `credit_workflow_events`. It has an `ON CONFLICT` idempotency clause. It does not reference `task_requests`, `nexus_durable_jobs`, department handoffs, HTTP, `pg_net`, webhooks, or Edge Function invocation.
- **OBSERVED FACT:** The `client_documents_client_insert_own` RLS policy permits an authenticated client to insert only an own-tenant client-portal document with `client_visible=true` and `approval_required=true`. That insert automatically creates a legacy credit-analysis queue record.
- **INFERENCE:** `CREDIT_REPORT_TRIGGER_ACTIVE=YES`, `CREDIT_REPORT_TRIGGER_AUTONOMOUS=YES` (event-driven), `CREDIT_REPORT_TRIGGER_CREATES_WORK=YES`, and `CREDIT_REPORT_TRIGGER_GOVERNED=NO` relative to the certified durable-job scheduler/dispatcher boundary. The database itself does not execute the resulting queue record; no live database worker/schedule was found.
- **RECOMMENDATION:** Preserve current business rows. Before activation, explicitly migrate this intake to the approved durable request/job boundary or isolate the legacy credit queue from every executor. No production change was made because the safe business transition and downstream consumer have not been proven.

## Other known work-creation paths

| Path | Trigger / authority | Writes | Automatic | Governance / role |
|---|---|---|---:|---|
| `queue_credit_report_after_upload()` | Authenticated own-tenant document insert | `credit_analysis_jobs`, `credit_document_workflows`, `credit_workflow_events` | Yes, on insert | Legacy queue; not durable-job governed |
| `request_credit_analysis_rerun(text,text)` | Explicit RPC request | `credit_analysis_jobs`, `credit_workflow_events`, workflow update | No | Security-definer; calls `nexus_is_active_admin()` and uses `auth.uid()`; no automatic schedule |
| `goclear_create_review_request(...)` | Explicit tenant request RPC | `client_tasks`, `goclear_followup_jobs` | No | Membership lookup and denial exception; creates GoClear product work, not Nexus durable jobs |
| `nexus_schedule_durable_jobs()` | Explicit service-role call | `nexus_durable_jobs`, schedule state | No database trigger/cron | Service-role only; intended external Nexus scheduler entry point |
| RLS writes to `task_requests` / `nexus_department_handoffs` | Authenticated request | Control-plane request/handoff rows | No | RLS policies require `nexus_is_active_admin()` |

- **OBSERVED FACT:** `nexus_durable_jobs` and `nexus_job_footprints` have RLS enabled, no policies, and no anon/authenticated insert grant. `task_requests` and `nexus_department_handoffs` policies target authenticated users and call the active-admin guard. No anon policy exists for these control-plane tables.
- **OBSERVED FACT:** Catalog ACLs show broad table INSERT grants to `anon` on some tables, but RLS has no anon policy for the control-plane tables. Effective anon control-plane work creation is therefore denied by RLS. Authenticated active admins can create task requests/handoffs by design; ordinary authenticated client sessions cannot.
- **OBSERVED FACT:** The `request_credit_analysis_rerun` function has anon/authenticated EXECUTE ACLs but is security-definer and checks the active-admin guard before its writes. It is a manual guarded operation, not an autonomous scheduler.
- **OBSERVED FACT:** The catalog and all deployed Edge Function source were inspected for Nexus task/job/handoff table references. No deployed Edge Function source referenced `task_requests`, `nexus_durable_jobs`, or `nexus_department_handoffs`.

## Deployed Edge Functions and source drift

- **OBSERVED FACT:** There are 17 deployed functions, all reported ACTIVE. All report a platform version and `verify_jwt` setting. Seven have platform JWT verification disabled; their source contains route-specific checks, but JWT configuration alone is not an authorization proof.
- **OBSERVED FACT:** Local source has 16 function directories (excluding `_shared`). `hermes-search` is local-only. `accept-guest-invitation` and `create-guest-invitation` are deployed but remote-only. Eight overlapping function source trees differ from their deployed source. No deployed function referenced Nexus durable-job tables.

| Deployed function | Provider call | Platform JWT | Local source | Governance result |
|---|---|---|---|---|
| `hermes-chat` | OpenRouter and Gemini | Required | Present, differs | BYPASS: direct paid calls without job/correlation identity or governor |
| `create-guest-invitation` | Resend | Required | Remote-only | BYPASS: direct email call without job/correlation identity or governor |
| `create-invited-checkout` | Stripe | Required | Present, differs | BYPASS: direct checkout call without job/correlation identity or governor |
| `create-stripe-checkout` | Stripe | Required | Present, differs | BYPASS: direct checkout call without job/correlation identity or governor |
| `goclear-followup-trigger` | Resend | Disabled | Present, differs | BYPASS: direct email call without job/correlation identity or governor |
| `goclear-marketing-send` | Resend | Disabled | Present, differs | BYPASS: direct email call without job/correlation identity or governor |
| `send-client-email` | Resend | Disabled | Present, differs | BYPASS: live source sends via Resend although local handler is fail-closed |

- **OBSERVED FACT:** The current registry contains 10 live Supabase provider candidate entries: 9 from prior local candidates plus the remote-only Resend caller. All 10 are classified active BYPASS in the registry; the 3 OpenRouter entries correspond to live fetch callsites in `hermes-chat`. One Google Workspace candidate is a static false positive because no deployed provider call was found.
- **OBSERVED FACT:** Live executable provider classes include OpenRouter, Gemini, Resend, and Stripe. `SUPABASE_PROVIDER_CALLERS_ACTIVE=10`, `SUPABASE_PROVIDER_GOVERNED_COUNT=0`, `SUPABASE_PROVIDER_BYPASS_COUNT=10`, `SUPABASE_PROVIDER_PARTIAL_COUNT=0` for registry callsite candidates.
- **OBSERVED FACT:** The local `send-client-email` fail-closed implementation is not the deployed implementation. This is material code/deployment drift.
- **RECOMMENDATION:** Do not route Nexus work to these functions until every live provider path is source-aligned and governed. No Edge Function was deployed, disabled, or invoked.

## RLS / execution authority

- **OBSERVED FACT:** RLS is enabled on `task_requests`, `nexus_durable_jobs`, `nexus_department_handoffs`, and `nexus_job_footprints`. Durable jobs and footprints expose no authenticated/anon insert privilege. Task request/handoff writes are active-admin guarded. `client_documents` allows only the constrained authenticated own-tenant upload policy for clients; that path is what fires the legacy credit trigger.
- **OBSERVED FACT:** `CLIENT_CAN_CREATE_CONTROL_PLANE_WORK=NO` for ordinary client sessions; `ANON_CAN_CREATE_CONTROL_PLANE_WORK=NO`; `UNEXPECTED_CONTROL_PLANE_WRITE_AUTHORITY=0` for Nexus durable/control-plane tables. Authenticated active-admin writes are expected authority.
- **UNKNOWN:** Project-level Auth hook config is not available through the tested management endpoint (HTTP 401). No Auth hook relation appeared in the SQL catalog; live database triggers on `auth.users` only call `goclear_handle_new_user`, which creates profile/membership records. This does not prove account-level Auth hook configuration is empty.

## Provider secret consumers (names only)

- **OBSERVED FACT:** Supabase secret metadata names were retrieved without placing values in reports. Downloaded deployed source maps names to consumers as follows:
  - `OPENROUTER_API_KEY`, `GEMINI_API_KEY` → `hermes-chat`.
  - `RESEND_API_KEY`, `RESEND_FROM_EMAIL` → `create-guest-invitation`, `goclear-followup-trigger`, `goclear-marketing-send`, `send-client-email`.
  - `STRIPE_SECRET_KEY` → `create-invited-checkout`, `create-stripe-checkout`.
  - `STRIPE_WEBHOOK_SECRET` → `stripe-webhook`; `RESEND_WEBHOOK_SECRET` → `goclear-resend-webhook`.
  - `SUPABASE_SERVICE_ROLE_KEY` → all 17 deployed functions; this is broad database authority and exceeds least privilege for many endpoints.
  - `SUPABASE_ANON_KEY` → 11 functions; `SUPABASE_URL` → all 17 functions.
- **OBSERVED FACT:** Deployed code references key names only; no key values were included in this report. Secret values were not requested from providers.
- **RECOMMENDATION:** Reduce service-role exposure by using narrower server-side RPC/roles for functions that only need scoped reads or writes. Preserve provider credentials until every consumer has a replacement.

## Webhooks and external control metadata

- **OBSERVED FACT:** No database webhook extension, `pg_net` network mechanism, or webhook-named database trigger was found. Two deployed Edge receivers exist: `goclear-resend-webhook` and `stripe-webhook`; both are HTTP endpoints, not scheduled database work.
- **UNKNOWN:** The authenticated project webhook-list and Auth-config Management API requests returned HTTP 401. Therefore provider-side webhook registrations and account-level Auth hook settings were not proven empty. The Edge receiver functions themselves are known and source-inspected.
- **INFERENCE:** No identified webhook path creates Nexus durable jobs or task requests. The unresolved endpoint metadata prevents claiming complete account-level webhook closure.

## Drift and closure decision

- **OBSERVED FACT:** `SUPABASE_SCHEMA_DRIFT=1 local-only migration`; remote migration table has 87 records and local timestamped files have 88. No migration was applied.
- **OBSERVED FACT:** `SUPABASE_EDGE_DRIFT=2 remote-only functions; 1 local-only function; 8 overlapping function trees differ`. The read-only JSON snapshot is `reports/remediation/supabase_remote_drift_20261009.json`.
- **OBSERVED FACT:** `SUPABASE_AUTOMATION_DRIFT=active legacy credit upload trigger; no database cron/network extension; account Auth/project webhook config returned 401`.
- **OBSERVED FACT:** Added `scripts/systems/supabase_remote_drift.py`. It runs only catalog SELECTs and `supabase functions list`, hashes function definitions/cron command text without emitting bodies, reports versions and drift, and has no authority to create work, call providers, deploy, enable runtime, or mutate the database. Running it produced the snapshot cited above.
- **DECISION:** `SUPABASE_BLOCKER_CLASS=BLOCKS_ACTIVATION`; `CORE_TRACK_B_ACTIVATION_READY=NO`. The active legacy trigger creates work outside the durable-job model, ten live provider callsite candidates bypass governance, and project Auth/webhook metadata is still denied. This is a specific live authority mismatch, not a generic unknown-only blocker.
- **RECOMMENDATION:** Keep scheduler and dispatcher OFF. Before reconsidering activation, define and approve a compatible credit-upload intake migration, source-align or disable the live bypassing Edge routes through a controlled deployment plan, and obtain scoped read access to Auth-hook/project-webhook metadata. Do not deploy or mutate production as part of this audit.

## Final values

```text
SUPABASE_CLI_INSTALLED=YES
SUPABASE_CLI_VERSION=2.90.0
SUPABASE_AUTH_VALID=YES_FOR_PROJECT_AND_SQL_CLI_PATHS; MANAGEMENT_AUTH_CONFIG=401
SUPABASE_PROJECT_LINKED=YES
SUPABASE_CRON_JOBS=0
SUPABASE_DATABASE_TRIGGERS=18
SUPABASE_EVENT_TRIGGERS=6
SUPABASE_NETWORK_CAPABLE_FUNCTIONS=0 live outbound SQL callers; 1 pg_net grant helper
SUPABASE_SECURITY_DEFINER_FUNCTIONS=20
CREDIT_REPORT_TRIGGER_ACTIVE=YES
CREDIT_REPORT_TRIGGER_AUTONOMOUS=YES_EVENT_DRIVEN
CREDIT_REPORT_TRIGGER_CREATES_WORK=YES_LEGACY_CREDIT_QUEUE
CREDIT_REPORT_TRIGGER_GOVERNED=NO
SUPABASE_EDGE_FUNCTIONS_DEPLOYED=17
SUPABASE_EDGE_FUNCTIONS_SOURCE_ONLY=1 (hermes-search)
SUPABASE_EDGE_FUNCTIONS_REMOTE_ONLY=2 (accept-guest-invitation, create-guest-invitation)
SUPABASE_WEBHOOKS=0_DATABASE_WEBHOOKS; 2_EDGE_RECEIVER_FUNCTIONS; PROJECT_ENDPOINT_API=401
SUPABASE_WEBHOOK_AUTONOMOUS_WORK_PATHS=0_IDENTIFIED
SUPABASE_AUTONOMOUS_DATABASE_WORK_PATHS=1 event-triggered legacy credit queue
SUPABASE_UNKNOWN_WORK_CREATION_PATHS=0 within inspected live DB catalog and deployed Edge source
SUPABASE_PROVIDER_CALLERS_ACTIVE=10 registry candidate entries
SUPABASE_PROVIDER_GOVERNED_COUNT=0
SUPABASE_PROVIDER_BYPASS_COUNT=10
SUPABASE_PROVIDER_PARTIAL_COUNT=0
CLIENT_CAN_CREATE_CONTROL_PLANE_WORK=NO ordinary client; upload can create legacy credit queue
ANON_CAN_CREATE_CONTROL_PLANE_WORK=NO
UNEXPECTED_CONTROL_PLANE_WRITE_AUTHORITY=0 for Nexus durable/control-plane tables
SUPABASE_REMOTE_SECRET_CONSUMERS=Mapped by deployed source names; service-role referenced by all 17 functions
SUPABASE_UNKNOWN_SECRET_CONSUMERS=0 code-level; platform implicit consumers not inferred
SUPABASE_SCHEMA_DRIFT=1_LOCAL_ONLY_MIGRATION
SUPABASE_EDGE_DRIFT=2_REMOTE_ONLY; 1_LOCAL_ONLY; 8_SOURCE_DIFFERS
SUPABASE_AUTOMATION_DRIFT=LEGACY_TRIGGER_ACTIVE; AUTH_AND_PROJECT_WEBHOOK_API_401
SUPABASE_REMOTE_DRIFT_ADAPTER_IMPLEMENTED=YES
SUPABASE_BLOCKER_CLASS=BLOCKS_ACTIVATION
CORE_TRACK_B_ACTIVATION_READY=NO
GLOBAL_PROVIDER_ENTRY_POINTS=159
GLOBAL_PROVIDER_GOVERNED_COUNT=26
GLOBAL_PROVIDER_NOT_APPLICABLE_COUNT=1
GLOBAL_PROVIDER_LEGACY_DISABLED_COUNT=0
GLOBAL_PROVIDER_BYPASS_COUNT=126
GLOBAL_PROVIDER_PARTIAL_COUNT=6
GLOBAL_PROVIDER_UNKNOWN_COUNT=0
NEW_SCHEDULER_RUNNING=NO
NEW_DISPATCHER_RUNNING=NO
CERTIFICATION_RESUMED=NO
SECRET_VALUES_IN_REPORTS=0
FINAL_STATUS=NEXUS_SUPABASE_CONTROL_PLANE_NOT_READY
```
