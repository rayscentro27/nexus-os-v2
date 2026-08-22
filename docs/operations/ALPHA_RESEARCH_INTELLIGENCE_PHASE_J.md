# Alpha Research Intelligence — Phase J

Alpha is Nexus's bounded external research and analysis capability. Hermes remains the operator and governed conversation surface; Alpha does not approve work, execute business actions, publish, trade, send messages, or access client PII.

## Canonical flow

`research objective → nexus.alpha-research-job.v1 → bounded research plan → existing search/source adapters → Nexus evidence ingestion → accepted nexus.evidence.v1 → Alpha claims and synthesis → nexus.alpha-research-pack.v1 → report and nexus.alpha-research-receipt.v1`

Alpha requests browser-backed acquisition through Nexus's `evidence_ingestion.crawl4ai` capability. Alpha never calls Modal, holds worker credentials/HMAC secrets, selects infrastructure, or receives unrestricted database access. Existing MarkItDown, YouTube/transcript, source-intake, model-router, memory, work-order, receipt, and Mission Control foundations remain the canonical integrations.

## Bounds and evidence policy

Every job is versioned, tenant-aware, serializable, freshness-aware, cost-aware, and bounded by source count, evidence jobs, model calls, runtime, and output size. The implementation defaults to ten sources, three evidence jobs, four model calls, two minutes, and 40,000 output characters, with hard upper bounds.

Claims carry an evidence reference, claim class (`DIRECT_EVIDENCE`, `DERIVED_ANALYSIS`, `INFERENCE`, or `UNKNOWN`), confidence, source quality, freshness, and contradiction notes. Unsupported claims are not presented as sourced facts. Conflicting claims are preserved with both evidence references. Old evidence is marked `AGING`, `STALE`, or `UNKNOWN`; it is not silently treated as current.

Canonical output is a structured research pack, with Markdown generated as a readable representation. Opportunity outputs are `RESEARCH_OPPORTUNITY_CANDIDATE` records only. They do not create work orders, applications, signups, payments, publishing, or revenue execution.

## Privacy and authority boundary

Requests containing SSNs, credit reports, bank/routing details, vault documents, credentials, private communications, or sensitive funding records are safety-blocked. Alpha has no service-role key, generic SQL path, unrestricted tenant-table access, direct Modal credential, worker HMAC, arbitrary shell, Stripe authority, broker authority, or consequential external action path. Public, generalized, and explicitly approved business context is the allowed scope.

## Failure semantics and certification

No useful evidence produces `INSUFFICIENT_EVIDENCE`; bounded dependency loss may produce `PARTIAL` or `FAILED`; safety violations produce `BLOCKED`. A remote-worker outage is optional capability degradation and must not change Continuous Loop, Active Operator, Recovery Check, Hermes, or core Mission Control health. Phase J is on-demand/governed; it adds no scheduler.

Live certification should use three public-only scenarios: competitor comparison, business/affiliate/funding opportunity research, and technology/open-source research. At least one scenario should use the existing Nexus → Modal → Crawl4AI route when that optional worker is available. If the worker or browser credentials are unavailable, record the truthful dependency state rather than fabricating evidence.

The next phase may govern opportunity candidates into records and revenue workflows. Phase J does not begin that Opportunity/Revenue Engine.

## Phase J-B live evidence bridge repair

The initial Phase J result was `PARTIAL` because the evidence CLI reported `DEPENDENCY_UNAVAILABLE`. Reproduction showed the failure happened before provider construction: `provider_from_environment()` required `NEXUS_MODAL_WORKER_URL` even though the certified native path uses `modal.Function.from_name(...).remote(...)`. The endpoint is now optional for native SDK mode and remains mandatory for the separate curl compatibility method. Modal profile, app name, HMAC signing, result validation, tenant validation, and canonical evidence acceptance remain unchanged.

Alpha's runtime bridge is Nexus-owned and fixed to one public URL, one `evidence_ingestion.crawl4ai` job, bounded limits, and the existing `accept_remote_evidence_result` path. Alpha receives accepted evidence fields only. It cannot select functions, access Modal credentials/HMAC, deploy, scale, read secrets, or invoke arbitrary commands. A successful run persists the existing research pack/report/receipt and writes the optional `nexus_alpha_research_heartbeat_latest.json`; Mission Control reads that heartbeat and exposes last job, receipt, source/evidence counts, freshness, and browser-evidence usage without affecting core health.

In this environment, the native Modal SDK was restored in the isolated agent environment and the authenticated `goclearonline` profile confirmed the deployed `nexus-remote-cpu-worker` app and `health_check`. The final browser-backed evidence submission still requires the dedicated worker HMAC from the secure runtime environment; that secret is not present locally and was not printed, reconstructed, or bypassed. Therefore a direct Crawl4AI evidence PASS cannot be claimed until the existing secure runtime injects that secret.

## Phase J-C final live certification

Phase J-C closed the remaining runtime blocker. The worker HMAC was rotated locally with cryptographically random material, written atomically to the canonical `$HOME/.config/nexus/runtime.env` with restrictive permissions, and synchronized to the existing Modal Secret referenced by `deploy/modal/modal_app.py`. The value was never printed, committed, placed in Alpha artifacts, or exposed to Hermes or Mission Control. The same `nexus-remote-cpu-worker` app was redeployed so fresh containers consume the synchronized secret; CPU-only, one-container, scale-to-zero behavior and the existing capability allowlist were preserved.

The signed Nexus → Modal → Crawl4AI → Chromium → `nexus.remote-result.v1` → Nexus evidence acceptance path passed for a benign public URL. A synthetic incorrect signature returned `UNAUTHORIZED`, proving HMAC enforcement remains active. The live Alpha open-source technology scenario then consumed a canonical `nexus.evidence.v1` artifact for the public Microsoft MarkItDown repository, produced a bounded research plan, evidence-linked claim, structured research pack, Markdown report, receipt, and Alpha heartbeat. Claim provenance was verified from claim to evidence ID to canonical artifact to the original public URL.

Mission Control reads Alpha as `HEALTHY`, optional, current, and browser-evidence-backed while Core Runtime, Active Operator, Recovery Check, Hermes, and Mission Control remain healthy. The three Phase J scenario families remain bounded and advisory; no opportunity execution, scheduler, consequential authority, or new research engine was added. Focused certification passed 40 tests, the Alpha TypeScript module typechecked, and its bundle build passed. Natural Recovery Check evidence remains the previously certified `PASS` milestone.
