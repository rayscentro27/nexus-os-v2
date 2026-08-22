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
