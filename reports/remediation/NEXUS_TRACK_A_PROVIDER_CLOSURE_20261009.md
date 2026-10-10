# Nexus Track A provider closure — 2026-10-09

## Outcome

**OBSERVED FACT:** Current registry size is 160. Current status counts: GOVERNED=39; DISABLED_FAIL_CLOSED=2; LEGACY_DISABLED=10; NOT_APPLICABLE=1; TEST_OR_MOCK=100; STATIC_FALSE_POSITIVE=5; DEAD_UNREACHABLE=0; BYPASS=3; PARTIAL=0; UNKNOWN=0.

**OBSERVED FACT:** All 123 previously flagged rows were classified: {'ACTIVE_REAL_RUNTIME_CALLER': 13, 'STATIC_FALSE_POSITIVE': 5, 'TEST_OR_MOCK': 100, 'LEGACY_DISABLED': 2, 'FINITE_EXTERNAL_BLOCKER': 3}. Runtime reachability unresolved=0 for the rows reviewed. The final bypass count is 3, all attached to explicit remote blockers; partial=0 and unknown=0. Caller-linked secret name mapping covers 123/123 rows. The broader local credential registry still reports dynamic/global consumers that cannot be certified to zero. `alpha_live_research.py` retains Supabase service-role access for direct research persistence and remains a least-privilege issue.

## Repairs

- Routed proactive Research public JSON, DuckDuckGo/Bing, and GitHub repository reads through `provider_enforcement.execute`, default-denying unknown hosts.
- Replaced Alpha heartbeat direct GitHub `urlopen`/`curl` fallback with governed requests.
- Routed YouTube intake and OANDA practice reads through a helper requiring durable job ID, correlation ID, department, and spend/usage authorization.
- Restricted YouTube key loading to the canonical runtime credential loader; removed repository `.env` lookup from the YouTube intake helper.
- Tightened the shared provider boundary to require explicit durable job, correlation, and department context.
- Required matching job and approval IDs before Resend/Stripe approval-lane sends.
- Restricted UI certification browser helpers to loopback; screenshot helper permits local files/loopback only.
- Disabled Firecrawl and TikTok network calls in canonical Netlify source until a governed deployment boundary exists.
- Disabled the legacy Hermes adapter before Supabase writes or subprocess launches.
- Corrected the Creative pilot scanner classification from browser to Modal; its Modal adapter already binds the submitted job to the durable job and invokes the shared governor.

## Sequential checks

- **PASS:** `.venv-agent-platform/bin/pytest -q scripts/nexus_agent_platform/tests/test_provider_enforcement.py scripts/nexus_agent_platform/tests/test_provider_surface_guard.py` — 15 passed.
- **PASS:** Python bytecode compilation for changed Python modules.
- **PASS:** `scripts/checks/provider_surface_guard.py` — no unscoped bypass, partial, or unknown rows; no drift in the hash-locked 81 reviewed local source files.
- **PASS:** Node native tests for disabled Firecrawl/TikTok paths — 2 passed.
- **PASS:** `node --check` for modified JavaScript modules.
- **INCOMPLETE:** Targeted Vitest invocation for `tests/alpha_url_review_safety.test.ts` started but did not report a result within the observation window and was interrupted to avoid leaving a hung process. Do not count frontend test as passing.

## Secret-consumer closure status

**OBSERVED FACT:** Caller-linked safe metadata mapping now covers 123/123 classified rows. A gated client-credit E2E suite no longer reads the Supabase service-role key; the Wave 1 helper reads only an explicit E2E variable allowlist from `.env.e2e.local`; a Stripe test checks non-secret mode metadata rather than loading the Stripe key.

**UNKNOWN:** `local_secret_consumer_registry_20261009.json` still flags dynamic/global consumers requiring review. The Research adapter continues to load Supabase service-role authority for direct persistence writes. Therefore global `UNKNOWN_LOCAL_SECRET_CONSUMERS=0` and `OVERPRIVILEGED_LOCAL_WORKERS=0` are not claimed.

## Remaining external blockers

- GitHub manual Pexels workflow remains reachable remotely and does not use the Nexus governor.
- Netlify deployed versions for TikTok and Firecrawl functions are not verified. Canonical source is fail-closed; remote deployment is not proven to match.

**RECOMMENDATION:** Keep staged activation closed until those 3 remote paths are disabled or proven to run under an approved governed boundary. Nexus scheduler, dispatcher, old kernel, and active operator remain OFF; certification remains NOT resumed.

## Final gate

```text
GLOBAL_PROVIDER_ENTRY_POINTS=160
GLOBAL_PROVIDER_GOVERNED_COUNT=39
GLOBAL_PROVIDER_DISABLED_COUNT=2
GLOBAL_PROVIDER_LEGACY_DISABLED_COUNT=10
GLOBAL_PROVIDER_NOT_APPLICABLE_COUNT=1
GLOBAL_PROVIDER_TEST_MOCK_COUNT=100
GLOBAL_PROVIDER_FALSE_POSITIVE_COUNT=5
GLOBAL_PROVIDER_DEAD_UNREACHABLE_COUNT=0
GLOBAL_PROVIDER_BYPASS_COUNT=3
GLOBAL_PROVIDER_PARTIAL_COUNT=0
GLOBAL_PROVIDER_UNKNOWN_COUNT=0
ACTIVE_REAL_RUNTIME_CALLERS=13
REMOTE_DEPLOYMENT_CALLERS=3
TEST_OR_MOCK_CALLERS=100
LEGACY_DISABLED_CALLERS=2
ADMIN_DIAGNOSTIC_CALLERS=0
DEAD_UNREACHABLE_CALLERS=0
STATIC_FALSE_POSITIVES=5
UNKNOWN_LOCAL_SECRET_CONSUMERS=NOT_CERTIFIED_ZERO
OVERPRIVILEGED_LOCAL_WORKERS=AT_LEAST_1
UNNECESSARY_LOCAL_SECRET_EXPOSURE=NOT_CERTIFIED_ZERO
RUNTIME_REACHABILITY_UNRESOLVED=0
PROVIDER_BYPASS_REGRESSION_GUARD=PASS_REVIEWED_SURFACE_HASH_LOCK; NEW FILE DISCOVERY NOT COVERED
TRACK_A_PROVIDER_CLOSURE_TESTS_PASS=YES_PYTHON_15_NODE_2
CORE_TRACK_B_ACTIVATION_READY=YES
INTERNAL_PRE_ACTIVATION_ZERO_UNKNOWN_PASS=NO
NEW_SCHEDULER_RUNNING=NO
NEW_DISPATCHER_RUNNING=NO
OLD_CONTINUOUS_KERNEL_RUNNING=NO
ACTIVE_OPERATOR_RUNNING=NO
CERTIFICATION_RESUMED=NO
SECRET_VALUES_IN_REPORTS=0
FINAL_STATUS=NEXUS_TRACK_A_PROVIDER_CLOSURE_NOT_READY
```

The remaining provider bypasses are the GitHub manual Pexels workflow and the two Netlify functions whose deployed versions are unknown. The local provider-surface guard hash-locks all 81 reviewed caller source files and validates registry classification, but does not automatically discover a brand-new source file. The local credential registry also does not certify all dynamic consumers. These are explicit closure gaps; no activation is authorized by this report.


## Final three provider + secret scope closure (2026-10-09)

See `reports/remediation/NEXUS_FINAL_THREE_PROVIDER_CLOSURE_20261009.md` for verified GitHub disablement, Netlify production deployment and handler checks, local loader changes, source scan results, test evidence, and remaining activation gaps. Scheduler/dispatcher remain OFF.

## Final three + secret scope closure (latest)

**OBSERVED FACT:** GitHub workflow `291709925` (`Render Short Video Maker`) is `disabled_manually` on `rayscentro27/nexuslive`. Its source remains preserved. Netlify production site `nexusv20` (`goclearonline.cc`) deployed commit `67c48700bdaf763a74dc4c4fb485189bd8727524` as ready deploy `6ac961d42a09190008b7ac16`. Public Alpha review and TikTok lifecycle route checks returned 503 `disabled_fail_closed`; no Firecrawl or TikTok provider call occurred.

**OBSERVED FACT:** The three prior external registry bypasses and three additional direct TikTok OAuth lifecycle callsites are now disabled and verified. Registry summary: 163 recorded rows; governed=39; disabled_fail_closed=8; legacy_disabled=10; not_applicable=1; test/mock=100; static_false_positive=5; dead=0; row bypass=0; row partial=0; row unknown=0.

**OBSERVED FACT:** Source-wide guard self-tests and focused safety tests passed: 22 Python tests and 3 Node tests. JavaScript syntax, Python compilation, and `git diff --check` passed. Secret-pattern scan over the reviewed reports and registries found zero matches.

**OBSERVED FACT:** Whole-source scan detected 45 provider-like source files, of which 35 are not represented by caller registry rows. The guard fails closed on those unregistered files. Effective source coverage is therefore not zero-unknown; `PROVIDER_BYPASS_REGRESSION_GUARD=NO` until those paths are individually classified and registered.

**OBSERVED FACT:** 41 runtime-env loader references now have 41 safe-metadata assessments. Python sensitive-key loading is deny-by-default with caller allowlists; the JavaScript loader now denies sensitive names unless explicitly allowlisted. Alpha live Research no longer loads or uses Supabase service-role for its legacy direct writes; those writes fail closed pending a job-scoped persistence bridge.

**UNKNOWN:** Dynamic/inherited local secret consumers and remaining control-plane service-role consumers are not certified zero. `UNKNOWN_LOCAL_SECRET_CONSUMERS=NOT_CERTIFIED_ZERO`; `OVERPRIVILEGED_LOCAL_WORKERS=NOT_CERTIFIED_ZERO`; `UNNECESSARY_LOCAL_SECRET_EXPOSURE=NOT_CERTIFIED_ZERO`.

```text
GITHUB_PEXELS_WORKFLOW_REMOTE_ENABLED=NO
GITHUB_PEXELS_WORKFLOW_GOVERNED=NO
GITHUB_PEXELS_BYPASS_REMAINING=0
NETLIFY_TIKTOK_REMOTE_STATE=DEPLOYED_FAIL_CLOSED_VERIFIED
NETLIFY_ALPHA_URL_REVIEW_REMOTE_STATE=DEPLOYED_FAIL_CLOSED_VERIFIED
NETLIFY_TIKTOK_BYPASS_REMAINING=0
NETLIFY_ALPHA_URL_REVIEW_BYPASS_REMAINING=0
BROAD_RUNTIME_ENV_LOADERS_TOTAL=41
BROAD_RUNTIME_ENV_LOADERS_ACTIVE=0
RESEARCH_SUPABASE_SERVICE_ROLE_DIRECT_ACCESS=NO
WHOLE_SOURCE_PROVIDER_SCAN=YES
NEW_PROVIDER_FILE_DISCOVERY=YES
UNREGISTERED_PROVIDER_CALL_FAILS_TEST=YES
PROVIDER_BYPASS_REGRESSION_GUARD=NO_UNREGISTERED_PROVIDER_LIKE_FILES_REMAIN
PROVIDER_GUARD_SELF_TESTS_PASS=YES
GLOBAL_PROVIDER_ENTRY_POINTS=163
GLOBAL_PROVIDER_GOVERNED_COUNT=39
GLOBAL_PROVIDER_DISABLED_COUNT=8
GLOBAL_PROVIDER_LEGACY_DISABLED_COUNT=10
GLOBAL_PROVIDER_NOT_APPLICABLE_COUNT=1
GLOBAL_PROVIDER_TEST_MOCK_COUNT=100
GLOBAL_PROVIDER_FALSE_POSITIVE_COUNT=5
GLOBAL_PROVIDER_DEAD_UNREACHABLE_COUNT=0
GLOBAL_PROVIDER_REMOTE_PRODUCTION_ISOLATED_COUNT=0
GLOBAL_PROVIDER_BYPASS_COUNT=0
GLOBAL_PROVIDER_PARTIAL_COUNT=0
GLOBAL_PROVIDER_UNKNOWN_COUNT=35
RUNTIME_REACHABILITY_UNRESOLVED=35
FINAL_TRACK_A_TESTS_PASS=YES_PYTHON_22_NODE_3
CORE_TRACK_B_ACTIVATION_READY=YES
INTERNAL_PRE_ACTIVATION_ZERO_UNKNOWN_PASS=NO
NEW_SCHEDULER_RUNNING=NO
NEW_DISPATCHER_RUNNING=NO
OLD_CONTINUOUS_KERNEL_RUNNING=NO
ACTIVE_OPERATOR_RUNNING=NO
CERTIFICATION_RESUMED=NO
SECRET_VALUES_IN_REPORTS=0
FINAL_STATUS=NEXUS_TRACK_A_FINAL_CLOSURE_NOT_READY
```

**DECISION:** The named GitHub and Netlify remote bypasses are closed. The final internal gate remains closed because 35 source surfaces and the broader secret least-privilege inventory still need resolution. Do not activate Nexus or resume certification.


Exact 35 unregistered provider-like source surfaces are listed in `reports/remediation/NEXUS_FINAL_THREE_PROVIDER_CLOSURE_20261009.md`.

## Final 35-file classification — 2026-10-09

**OBSERVED FACT:** The exact 35 unregistered files were classified and added to the caller registry. All provider-like source files are now registered; whole-source guard passes with no unregistered files, bypass, partial, or unknown rows.

**OBSERVED FACT:** The 41 broad-loader references are assessed as narrow scoped, with zero active workflow processes. Research direct service-role access is NO. Credential names and metadata only are in the secret registry.

**TEST:** Focused final-35 suite: 23 passed. No provider calls, browser automation, or heavy models were run.
