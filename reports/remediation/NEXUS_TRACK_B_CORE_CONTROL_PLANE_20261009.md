# NEXUS TRACK B CORE CONTROL-PLANE CLOSURE

## Safe mode

- **OBSERVED FACT:** Safe mode remained active. Scheduler, dispatcher, old kernel, active operator, and certification remained off. No external writes, deployments, provider actions, Meta API calls, or paid workloads were run.

## Meta quarantine

- **OBSERVED FACT:** The local `nexuslive/.env` Vite Meta and Gemini private-key inputs were found to match values in its generated JavaScript artifact. The exposed Meta Vite value was different from the Meta value in canonical `~/.config/nexus/runtime.env`.
- **OBSERVED FACT:** Both Vite private credential inputs were moved to a mode-0600 forensic env file under a mode-0700 `~/.nexus/forensics/meta_quarantine_20261009` directory. Meta credential entries were also quarantined from the legacy secondary checkout env file. Values were not emitted.
- **OBSERVED FACT:** The contaminated `nexuslive/dist` tree was copied byte-for-byte into the restricted forensic directory, verified by per-file SHA-256 comparison, then removed from the build-serving path. Nine generated files (about 1.97 MB) were retained. The public artifact evidence remains in the forensic copy.
- **OBSERVED FACT:** Canonical `~/.config/nexus/runtime.env` contains the newer Meta key name and has mode 0600. The current local Meta credential is not Vite-prefixed; targeted client source scan found no Meta/Gemini private variable references.
- **INFERENCE:** There are zero active local consumers of the old exposed value after removing its runtime env names and generated bundle. The forensic vault is not in a build/runtime search path.
- **UNKNOWN:** Provider-side revocation is not performed. The exact public deployment containing the old credential cannot be tied to a Netlify deploy without deploy metadata.
- **HUMAN ACTION REQUIRED:** Revoke the old exposed Meta credential in Meta’s account console. Do not paste the credential into chat.

## Supabase

- **OBSERVED FACT:** A local Supabase CLI exists, but `supabase projects list` timed out. A bounded read-only REST OpenAPI/auth-settings request using the locally stored anon credential failed at network/API transport. No service-role request or mutation was made.
- **OBSERVED FACT:** The canonical Git index contains 17 Supabase function source files (including shared code). The existing static caller registry had 10 Supabase Edge candidates: 9 were already fail-closed/legacy-disabled; `send-client-email` was reclassified `LEGACY_DISABLED` because current handler source returns a 503 before its old provider-send body.
- **UNKNOWN:** Deployed Edge Function versions/auth, `queue_credit_report_after_upload()` definition, triggers, pg_cron, pg_net, webhooks, RLS/grants/security-definer execution, Realtime, Storage policies, and autonomous task/job creation. The deployed bypass count is unknown because the remote deployment could not be inspected.
- **DECISION:** `SUPABASE_BLOCKER_CLASS=BLOCKS_ACTIVATION`. The deployed automation boundary cannot yet be proven safe or isolated.

## GitHub

- **OBSERVED FACT:** GitHub API access succeeded for `rayscentro27/nexus-os-v2` and `rayscentro27/nexuslive`; both are public and use `main`. Canonical GitHub `main` is `8d624f5eedf0c155b042e9b9f569664c4534c29e`, matching the verified local commit.
- **OBSERVED FACT:** Canonical repo has zero remote Actions workflows, runs, environments, repository secret names, variables, hooks, deploy keys, runners, rulesets, or deployments. Actions are enabled, allowed actions are `all`, and SHA pinning is not required. Branch protection endpoint was inaccessible.
- **OBSERVED FACT:** `nexuslive` has two active `workflow_dispatch` workflows, no `schedule`/push/PR triggers, no webhooks, no self-hosted runners, and no deployment steps. Recent visible runs were manual artifact renders from June 8–9, 2026. One workflow consumes repository secret name `PEXELS_API_KEY` and calls Pexels for artifact-only media selection; the other renders an MP4 artifact. Neither has Nexus task/job creation or publication in its workflow source.
- **OBSERVED FACT:** GitHub’s exposed deployment/workflow surfaces show no autonomous Nexus schedule. GitHub Apps and branch governance remain unknown; local Netlify configuration says GitHub `main` auto-deploy is intended, but Netlify’s site integration cannot be confirmed.
- **DECISION:** `GITHUB_BLOCKER_CLASS=SAFE_FOR_STAGED_ACTIVATION`; keep the manual Pexels workflow classified as a provider bypass and out of Nexus runtime activation.

## Netlify

- **OBSERVED FACT:** Netlify CLI is present but its version, status, and site listing hung in the prior bounded check; it remains classified unreliable. No CLI deploy was run.
- **OBSERVED FACT:** Canonical `netlify.toml` declares `node scripts/deployment/cloud_build.mjs`, publishes `dist`, and uses `netlify/functions`. It states GitHub `main` auto-deploy is enabled at site level. Nineteen Netlify function source files are tracked. Source includes the auth/approval-gated `creative-review-write` request path; no scheduled-function marker was found in the tracked function source.
- **UNKNOWN:** Production site/domain, Git repo/branch/commit, deploy ID/time, current deployed functions, schedules, build hooks, and environment-variable names. The old public Meta bundle cannot be mapped to a specific Netlify deploy.
- **INFERENCE:** Tracked Netlify functions are request-driven; no autonomous scheduler is evidenced locally. `creative-review-write` is a request path and includes auth/approval markers; it is not evidence of autonomous job execution.
- **DECISION:** `NETLIFY_BLOCKER_CLASS=BLOCKS_PRODUCTION_ONLY`; dashboard confirmation is required before production certification/deployment. The intended Git auto-deploy path is local-config evidence only.

## Other providers

- **INFERENCE:** Cloudflare and R2 are `NOT_CURRENTLY_IN_RUNTIME`; canonical repo has no Wrangler config/dependency and no verified integration. Oracle, Modal, Hugging Face, and Kaggle remain `BLOCKS_PROVIDER_ONLY` for their respective jobs; no evidence in this pass shows autonomous Nexus execution. These providers do not block Mac-only staged activation.

## Track A registry reconciliation

- **OBSERVED FACT:** Reclassified one Supabase source candidate from `BYPASS` to `LEGACY_DISABLED` based on the source fail-closed return, while recording deployed state as unknown. Added the active manual Pexels GitHub workflow as a governed-incomplete `BYPASS` caller. Updated registry totals: 158 entry points, 26 governed, 10 legacy-disabled, 116 bypass, 6 partial, 0 scanner-unknown. Track A’s broader caller closure remains incomplete.

## Gate

- **OBSERVED FACT:** `CORE_TRACK_B_ACTIVATION_READY=NO` because deployed Supabase autonomous execution remains unknown. GitHub does not block staged activation based on accessible remote metadata. Netlify requires confirmation for production only.
- **OBSERVED FACT:** `SECRET_VALUES_IN_REPORTS=0`; no secret values are included in this report or machine-readable closure output.
- **RECOMMENDATION:** Keep scheduler and dispatcher off. Obtain Supabase management/catalog access to map the deployed automation boundary; separately complete Meta revocation and Netlify production identity before production deployment.

## Edge/function/workflow caller reconciliation (source versus deployment)

| Caller ID | Function | Provider | Deployed | Active in source | Governed | Partial | Bypass | Legacy disabled | Spend | Write |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| `caller.5db2cd4cc21be160` | `supabase/functions/hermes-chat/index.ts :: module_scope` | GEMINI | UNKNOWN | FALSE | FALSE | FALSE | FALSE | TRUE | TRUE | FALSE |
| `caller.60da8b2db226bb81` | `supabase/functions/hermes-chat/index.ts :: module_scope` | GOOGLE_WORKSPACE | UNKNOWN | FALSE | FALSE | FALSE | FALSE | TRUE | FALSE | FALSE |
| `caller.c39be15dfac125f1` | `supabase/functions/hermes-chat/index.ts :: callOpenRouter` | OPENROUTER | UNKNOWN | FALSE | FALSE | FALSE | FALSE | TRUE | TRUE | FALSE |
| `caller.ed54e5f5922c154d` | `supabase/functions/hermes-chat/index.ts :: callOpenRouterNative` | OPENROUTER | UNKNOWN | FALSE | FALSE | FALSE | FALSE | TRUE | TRUE | FALSE |
| `caller.17fea63bb0745af0` | `supabase/functions/hermes-chat/index.ts :: module_scope` | OPENROUTER | UNKNOWN | FALSE | FALSE | FALSE | FALSE | TRUE | TRUE | FALSE |
| `caller.3c4bf14d6d280dac` | `supabase/functions/goclear-followup-trigger/index.ts :: json` | RESEND | UNKNOWN | FALSE | FALSE | FALSE | FALSE | TRUE | TRUE | TRUE |
| `caller.697371b7fe1550f2` | `supabase/functions/goclear-marketing-send/index.ts :: json` | RESEND | UNKNOWN | FALSE | FALSE | FALSE | FALSE | TRUE | TRUE | TRUE |
| `caller.0209bd8648eb3ee0` | `supabase/functions/send-client-email/index.ts :: module_scope` | RESEND | UNKNOWN | FALSE | FALSE | FALSE | FALSE | TRUE | TRUE | TRUE |
| `caller.2e45a97482b9ad41` | `supabase/functions/create-invited-checkout/index.ts :: module_scope` | STRIPE | UNKNOWN | FALSE | FALSE | FALSE | FALSE | TRUE | TRUE | TRUE |
| `caller.788657ba0316128b` | `supabase/functions/create-stripe-checkout/index.ts :: resolveStripeRuntime` | STRIPE | UNKNOWN | FALSE | FALSE | FALSE | FALSE | TRUE | TRUE | TRUE |
| `caller.74a4f533f6075077` | `github:rayscentro27/nexuslive/.github/workflows/render-short-video-maker.yml :: workflow_dispatch.render` | PEXELS | ACTIVE_WORKFLOW | TRUE | FALSE | FALSE | TRUE | FALSE | FALSE | FALSE |
| `caller.35a8e547abb024b0` | `netlify/functions/_tiktok.mjs :: tiktok_api_request` | TIKTOK | UNKNOWN | TRUE | FALSE | FALSE | TRUE | FALSE | TRUE | TRUE |
| `caller.93fda6812843ed40` | `netlify/functions/alpha-url-review.mjs :: firecrawl_review` | FIRECRAWL | UNKNOWN | TRUE | FALSE | FALSE | TRUE | FALSE | TRUE | FALSE |

**OBSERVED FACT:** Current-source status does not prove remote deployment status. Supabase rows marked legacy-disabled have not been checked against deployed versions. Netlify candidates are source-only and remain deployment-unknown. The GitHub Pexels workflow is an active manual workflow and remains a provider bypass; it does not create Nexus work in its workflow source.


## Superseding live Supabase control-plane closure — 2026-10-09

- **OBSERVED FACT:** The earlier statement that Supabase CLI project access timed out is superseded. Authenticated CLI project listing, linked migration inventory, SQL catalog reads, deployed function metadata, and deployed source downloads succeeded.
- **OBSERVED FACT:** Live PostgreSQL has no `pg_cron`/`pg_net`; it has 18 enabled triggers and 6 platform event triggers. `queue_credit_report_after_upload()` automatically creates legacy credit-analysis workflow rows on client document upload; no DB HTTP invocation or durable Nexus job insertion occurs.
- **OBSERVED FACT:** Seventeen Edge Functions are deployed. Two have no local source, one local function is not deployed, eight overlapping function trees differ, and ten Supabase provider registry candidates are active bypasses. `send-client-email` is especially drifted: live code reaches Resend although local code fails closed.
- **UNKNOWN:** Auth hook and project webhook Management API requests returned HTTP 401. Database catalog evidence shows no pg_net/database webhook mechanism, but account-level Auth/project webhook settings remain inaccessible.
- **DECISION:** `SUPABASE_BLOCKER_CLASS=BLOCKS_ACTIVATION`; the blocker is specific: legacy event-driven credit queue plus active ungoverned provider endpoints, with inaccessible Auth/webhook administration as an additional gap.
- **OBSERVED FACT:** Read-only drift adapter added at `scripts/systems/supabase_remote_drift.py`; snapshot at `reports/remediation/supabase_remote_drift_20261009.json`. No remote mutation or runtime activation occurred.

**CORE_TRACK_B_ACTIVATION_READY=NO**
**FINAL_STATUS=NEXUS_SUPABASE_CONTROL_PLANE_NOT_READY**


## Supabase live remediation — 2026-10-09 (supersedes previous Supabase status)

**OBSERVED FACT:** Migration `20261021170000_credit_upload_durable_job_transition.sql` is applied. The live upload trigger enqueues the existing durable queue with tenant/client/document/job/correlation/governance metadata and no longer inserts `credit_analysis_jobs`. Authenticated clients cannot directly insert/read durable jobs; anon has no insert authority. A rollback-only authenticated synthetic canary observed one durable job, zero legacy rows, and one workflow row, then rolled back completely. Existing 25 legacy credit rows (13 queued) and 8 durable jobs were preserved.

**OBSERVED FACT:** Seven provider-action Edge functions were deployed fail-closed with existing JWT settings. The 10 formerly live Resend/Stripe/OpenRouter/Gemini candidate callsites are now disabled; no provider request occurred. Fresh deployed source matched local source for all seven endpoints. 17 functions remain deployed, 0 remote-only; `hermes-search` is the single local-only source. Two intentionally different trees (`create-tester-invitation`, `stripe-webhook`) are documented with hashes/behavior notes; unexplained drift is zero.

**OBSERVED FACT:** Focused Python/pytest/static checks and live rollback canary passed. Runtime remains OFF and certification did not resume. Full details: `reports/remediation/NEXUS_SUPABASE_REMEDIATION_20261009.md`.

**DECISION:** `SUPABASE_BLOCKER_CLASS=SAFE_FOR_STAGED_ACTIVATION`; `CORE_TRACK_B_ACTIVATION_READY=YES`. Global Track A provider bypasses remain; do not enable scheduler/dispatcher based on this Supabase-only pass.


### Supabase follow-up privilege closure

**OBSERVED FACT:** Post-remediation drift inspection found `anon` retained EXECUTE on the manual `request_credit_analysis_rerun(text,text)` RPC. The function already checked active-admin status, but anonymous EXECUTE was unnecessary. Additive migration `20261021180000_revoke_anon_credit_rerun.sql` now revokes `PUBLIC` and `anon`, retaining authenticated/service-role execution and the active-admin guard. Live verification: anonymous EXECUTE `false`, authenticated EXECUTE `true`; migration head `20261021180000`; local and remote migrations in sync. Credit queue counts remained 25 total / 13 queued; durable rows remained 8; no canary rows remain.

**DECISION:** Supabase remains `SAFE_FOR_STAGED_ACTIVATION`; Nexus runtime remains OFF and the global pre-activation gate remains closed.
