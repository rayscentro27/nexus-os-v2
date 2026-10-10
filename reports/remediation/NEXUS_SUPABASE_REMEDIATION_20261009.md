# NEXUS SUPABASE LIVE REMEDIATION

Status recorded 2026-10-09. Project ref: `iqjwgpnujbeoyaeuwehj`.

## Result

- **OBSERVED FACT:** Safe mode stayed active. Scheduler, dispatcher, old continuous kernel, active operator, PM2 workflow processes, and certification remain OFF.
- **OBSERVED FACT:** New credit-report uploads now enter the existing `nexus_durable_jobs` queue via the `client_documents` trigger. The trigger no longer creates `credit_analysis_jobs` rows.
- **OBSERVED FACT:** Seven deployed Edge endpoints that previously made Resend, Stripe, OpenRouter, or Gemini calls now return a fail-closed 503 before loading provider credentials or making outbound requests. Their JWT settings were preserved.
- **OBSERVED FACT:** A synthetic authenticated upload canary inside a rollback-only subtransaction verified one durable job, zero legacy jobs, and one workflow row. The transaction rolled back; no canary data or durable job remains.
- **OBSERVED FACT:** No email, payment, model, publish, or other provider action was executed.
- **DECISION:** `SUPABASE_BLOCKER_CLASS=SAFE_FOR_STAGED_ACTIVATION`; this is a Supabase-only decision. The global Nexus pre-activation gate remains closed because non-Supabase provider candidates remain outside this pass.

## Pre-change evidence and rollback

The restricted snapshot is under `reports/remediation/evidence/supabase_prechange_20261009/`. The live trigger/function definitions, migration head, and queue counts are in `live_prechange_snapshot.json`; deployed Edge names/version/JWT/bundle metadata is in `edge_functions.json`; all 17 deployed function sources are preserved in `deployed_edge_source_before/`; the replaced local provider source is preserved in `local_edge_source_before/`. Evidence files are mode 0600 and directories mode 0700. `rollback_notes.md` records rollback steps and the migrations applied.

## Legacy credit queue dependency map

| Component | Reads/writes | Role and classification |
|---|---|---|
| `public.queue_credit_report_after_upload()` | Now writes `nexus_durable_jobs`, `credit_document_workflows`, `credit_workflow_events`; no longer writes `credit_analysis_jobs` | `ACTIVE_REQUIRED`; authenticated own-tenant upload trigger; governed queue creation with explicit non-provider governance context |
| `scripts/credit/process_credit_analysis_queue.py` | Reads/claims/updates `credit_analysis_jobs`; invokes the parser | `LEGACY_ACTIVE / JOB_ONLY`; bounded one-shot legacy consumer. No autonomous startup is enabled. It is retained for historical queued rows and rollback; do not invoke during safe mode. |
| `scripts/credit/parse_uploaded_credit_report.py` | Reads document metadata/storage; writes parser results, review/canonical analysis tables, workflow state, and events | `ACTIVE_REQUIRED`; now accepts durable `--nexus-job-id` identity and persists that identity on parser results/events. No provider call is part of this local parser path. |
| `scripts/nexus_agent_platform/job_worker_once.py` | Claims a durable job through the standard dispatcher and invokes the credit parser once | `ACTIVE_REQUIRED / JOB_ONLY`; allowlisted `CREDIT_REPORT_ANALYSIS` route; normal governor envelope, footprint and receipt path applies. |
| `src/components/client/InlineDocumentUpload.jsx` | Previously attempted a second direct insert into `credit_analysis_jobs` | Repaired; it now relies on the single database trigger and has no direct legacy enqueue. |
| `public.request_credit_analysis_rerun(text,text)` and admin recovery UI | Explicit active-admin reruns still use `credit_analysis_jobs` and the retained legacy worker | `LEGACY_ACTIVE / MANUAL_ADMIN_ONLY`; no schedule or automatic upload link. Retain for rollback/history pending migration of admin recovery semantics. |
| Synthetic tester scripts | Seed/inspect/reset synthetic credit certification fixtures | `JOB_ONLY / TEST`; never enabled by this remediation. |

**OBSERVED FACT:** Before the change there were 25 legacy credit rows (13 queued, 12 complete), 25 workflow rows (13 queued, 12 complete), and 8 durable jobs. After migration and canary rollback the counts remain unchanged. No historical row was claimed, retried, completed, deleted, or migrated.

**OBSERVED FACT:** A follow-up migration `20261021180000_revoke_anon_credit_rerun.sql` removed `anon` EXECUTE from the legacy admin-rerun RPC; authenticated and service-role grants remain, and the function retains its active-admin guard. Live verification reports `anon_can_execute=false`, `authenticated_can_execute=true`.

The legacy queue is not ready for deletion. Its 13 pending historical rows and explicit admin rerun path remain. Current classification: `STILL_REQUIRED_FOR_ROLLBACK`; reconsider after certification and after old manual recovery is moved to durable jobs.

## Durable upload job contract

Migration `20261021170000_credit_upload_durable_job_transition.sql` adds `tenant_id`, `client_id`, `source_document_id`, and object-valued `governance_context` to the existing durable job table, plus `nexus_job_id` to parser results. It replaces the trigger implementation but retains the existing trigger and legacy table.

The trigger accepts only credit-report categories from an authenticated tenant member and `source='client_portal_upload'`, `client_visible=true`, and `approval_required=true`. It inserts one `CREDIT_BUSINESS_FUNDING / CREDIT_REPORT_ANALYSIS` durable job with a generated job ID, generated correlation ID, source document identity, and deterministic `credit-report-upload:<document>` idempotency key. The governance context records the trigger policy and explicitly states `paid_provider_authorized=false` and `external_actions_authorized=false`. It creates the workflow row and queued/upload events. It does not insert a legacy credit job or call HTTP/Edge/provider code.

The existing dispatcher’s `CREDIT_REPORT_ANALYSIS` handler requires `source_document_id` to equal the payload document ID; it runs the parser as a one-shot child, passes the durable job identity, and leaves standard durable completion footprint/receipt handling in place. This work type counts as heavy for host-resource caps.

**OBSERVED FACT:** `nexus_durable_jobs` has no anon/authenticated INSERT grants and no anon/authenticated INSERT/ALL RLS policies. The canary upload through the authenticated client role succeeded; attempting to read the durable table as that client was denied. The trigger’s SECURITY DEFINER path created the job under database ownership. No client-supplied job ID or provider authority is accepted.

## Live canary

**OBSERVED FACT:** A dedicated synthetic test persona and membership were present. A rollback-only PL/pgSQL subtransaction simulated the authenticated upload role and verified `document_insert_accepted=true`, `durable_jobs_created=1`, `legacy_jobs_created=0`, and `workflow_rows_created=1`. The intentional exception rolled back the insert and all trigger effects. A follow-up read verified zero canary documents and unchanged aggregate queue counts.

## Supabase migrations and automation

- **OBSERVED FACT:** Live migration head is `20261021180000`; both the durable upload transition and follow-up anon RPC privilege migration are recorded as applied.
- **OBSERVED FACT:** `pg_cron` remains absent and there are zero cron jobs. `pg_net` remains absent; no database HTTP/network-capable execution was introduced.
- **OBSERVED FACT:** The document trigger remains enabled and is event-driven only. The durable scheduler RPC remains a service-role scheduler operation and no database cron/trigger invokes it.
- **OBSERVED FACT:** The only change outside the credit transition was the pending idempotent Telegram governor migration, which inserts disabled daily/monthly policies.
- **UNKNOWN / EXTERNAL:** Supabase Management API Auth configuration and account-level project-webhook metadata endpoints returned 401 for the locally stored CLI identity. Database catalog inspection found no `pg_cron`, `pg_net`, Supabase HTTP trigger schema, or database webhook path. Account-level metadata is not represented as empty by this report.

## Supabase Edge provider callers: 10 source candidates

The first six function names below were the local/deployed direct provider paths; `create-guest-invitation` was remote-only and is now represented locally by a fail-closed replacement. Line numbers identify pre-change deployed source. All seven endpoints remain deployed/ACTIVE as HTTP functions, but provider actions are disabled in code.

| Function / pre-change callsite | Provider | Purpose | Pre-change behavior | Current deployed and local behavior | Job/correlation/governor/approval before action | Spend/write | Status |
|---|---|---|---|---|---|---|---|
| `hermes-chat` (OpenRouter lines 1118, 1166, 2091) | OpenRouter | Chat/model fallback calls | Direct paid model requests | Fail-closed 503; no credential read or fetch | No such contract was present; call disabled | Spend | `LEGACY_DISABLED` |
| `hermes-chat` (Gemini line 2133) | Gemini | Chat/model call | Direct paid model request | Fail-closed 503; no credential read or fetch | No such contract was present; call disabled | Spend | `LEGACY_DISABLED` |
| `create-guest-invitation` (line 35) | Resend | Guest invitation email | Remote-only function sent email | Fail-closed 503; no credential read or fetch | No such contract was present; call disabled | Spend/write | `LEGACY_DISABLED` |
| `create-invited-checkout` (line 135) | Stripe | Create checkout session | Direct Stripe checkout creation | Fail-closed 503; no credential read or fetch | No job, correlation, governor, or approval boundary; call disabled | Spend/write | `LEGACY_DISABLED` |
| `create-stripe-checkout` (line 92) | Stripe | Create checkout session | Direct Stripe checkout creation | Fail-closed 503; no credential read or fetch | No job, correlation, governor, or approval boundary; call disabled | Spend/write | `LEGACY_DISABLED` |
| `goclear-followup-trigger` (line 44) | Resend | Follow-up email | Direct Resend send; JWT verification off | Fail-closed 503; JWT remains off; no credential read/fetch | No such contract was present; call disabled | Spend/write | `LEGACY_DISABLED` |
| `goclear-marketing-send` (line 26) | Resend | Marketing email | Direct Resend send; JWT verification off | Fail-closed 503; JWT remains off; no credential read/fetch | No such contract was present; call disabled | Spend/write | `LEGACY_DISABLED` |
| `send-client-email` (line 256) | Resend | Client email | Deployed code sent directly; JWT verification off | Fail-closed 503; JWT remains off; deployed source parity verified | No such contract was present; call disabled | Spend/write | `LEGACY_DISABLED` |

**OBSERVED FACT:** Seven updated functions were deployed sequentially and each preserved its pre-change JWT verification setting. Post-deploy function metadata version advanced; a fresh download confirmed the deployed and local source are byte-identical for all seven. No function was invoked for this verification. No provider keys or secret values appear in reports.

**OBSERVED FACT:** Active provider caller count is now 0; 10 discovered provider callsites are disabled, 0 governed-active, 0 bypass, and 0 partial. `send-client-email` is disabled, not governed. Provider capability can be restored only after a real durable job/correlation identity, usage/money authorization, approval for external writes, and receipt/footprint are implemented.

## Edge source/deployment reconciliation

- **OBSERVED FACT:** All 17 deployed function names now have local source; remote-only count is 0. The two previously remote-only invitation function sources were preserved before change; accept-guest-invitation is copied locally unchanged and create-guest-invitation’s pre-change source is in restricted evidence.
- **OBSERVED FACT:** One local-only function remains, `hermes-search`; it was not deployed.
- **OBSERVED FACT:** A fresh post-deploy download found 15 deployed/local source trees byte-identical. Two source trees remain intentionally different and are not unexplained drift:
  - `create-tester-invitation`: local and deployed versions reference the same invitation/admin/payment-pilot tables and Supabase auth variables. It has no direct Resend/Stripe/OpenRouter/Gemini provider call. It was not changed or redeployed; downstream `send-client-email` is fail-closed.
  - `stripe-webhook`: inbound signed Stripe event handler with database writes to client order/payment/referral/service-fulfillment tables. Local code has mode-specific webhook secret-name selection while deployed source uses the generic webhook secret name. No outbound Stripe call was found. Both versions were preserved; no webhook cutover was attempted.
- **OBSERVED FACT:** `SUPABASE_EDGE_FUNCTIONS_UNEXPLAINED_DRIFT=0`; `SUPABASE_EDGE_FUNCTIONS_REMOTE_ONLY=0`. The two intentional source differences are listed above and in `edge_source_parity_after.json`.

## Focused validation

- **PASS:** Python compilation for durable-job model, worker, and credit parser.
- **PASS:** 6 focused pytest cases covering the credit durable job contract, idempotency/routing, Supabase projections, fail-closed provider endpoints, and non-mutating preflight behavior.
- **PASS:** Existing bounded credit queue and credit workflow migration checks.
- **PASS:** Live migration dry run showed the two pending migrations; live `supabase db push --linked --yes` applied them successfully.
- **PASS:** Live canary rollback result described above.
- **NOT RUN:** No real provider call, email, checkout, or live document processing was performed. No runtime activation occurred.

## Final state

```text
DOCUMENT_UPLOAD_CREATES_DURABLE_JOB=YES
DOCUMENT_UPLOAD_CREATES_LEGACY_CREDIT_JOB=NO
DUPLICATE_JOB_CREATION=0
CLIENT_DIRECT_DURABLE_JOB_INSERT=NO
ANON_DIRECT_DURABLE_JOB_INSERT=NO
TRIGGER_GOVERNED_JOB_CREATION=YES
SUPABASE_PROVIDER_CALLERS_ACTIVE=0
SUPABASE_PROVIDER_DISABLED_COUNT=10
SUPABASE_PROVIDER_BYPASS_COUNT=0
SUPABASE_PROVIDER_PARTIAL_COUNT=0
SUPABASE_EDGE_FUNCTIONS_DEPLOYED=17
SUPABASE_EDGE_FUNCTIONS_REMOTE_ONLY=0
SUPABASE_EDGE_FUNCTIONS_UNEXPLAINED_DRIFT=0
SUPABASE_UNKNOWN_WORK_CREATION_PATHS=0
CREDIT_ANALYSIS_JOBS_STATUS=STILL_REQUIRED_FOR_ROLLBACK
SUPABASE_SCHEMA_DRIFT=0_EXPECTED (migration head 20261021180000)
SUPABASE_EDGE_DRIFT=2_INTENTIONALLY_DIFFERENT_SOURCE_TREES
SUPABASE_AUTOMATION_DRIFT=0_UNEXPLAINED
SUPABASE_BLOCKER_CLASS=SAFE_FOR_STAGED_ACTIVATION
CORE_TRACK_B_ACTIVATION_READY=YES
NEW_SCHEDULER_RUNNING=NO
NEW_DISPATCHER_RUNNING=NO
CERTIFICATION_RESUMED=NO
SECRET_VALUES_IN_REPORTS=0
FINAL_STATUS=NEXUS_SUPABASE_REMEDIATION_PASS
```

**RECOMMENDATION:** Keep all Nexus execution disabled. The Supabase control plane is ready for a later staged activation from the durable-job path, but this report does not close the other global provider callers or authorize re-enabling any provider endpoint.
