# Nexus Systems Ledger

This is the repository's canonical architecture decision ledger. Repository
inspection found no existing file-backed Systems Ledger; the existing events
feed ledger is an event summarizer, not an architecture decision register.

## NEXUS_STORAGE_ARCHITECTURE_R2_CANONICAL_MEDIA_R1

- **Status:** ACTIVE / AUTHORITATIVE
- **Decision:** Cloudflare R2 is the canonical object/media storage layer for
  Nexus Creative assets and large media. Supabase is the canonical metadata,
  business, workflow, relationship, approval, and indexing layer. Execution
  environments are temporary producers and do not own permanent assets.
- **Reason:** Nexus generates content in multiple execution environments. A
  single canonical object store is required for predictable retrieval,
  provenance, cost control, Creative Studio visibility, and reduced Supabase
  media traffic.
- **Rules:**
  1. R2 owns canonical media bytes.
  2. Supabase owns metadata and workflow/business state.
  3. Large media binaries are not stored in Supabase database fields.
  4. Execution environments are temporary.
  5. Asset Persistence Bot is the canonical ingestion path.
  6. Creative jobs are incomplete until R2 ingestion and Supabase metadata
     registration succeed.
  7. Signed/governed object access is preferred over permanent public URLs.
  8. Content hashes are used for deduplication.
  9. This decision remains authoritative until explicitly superseded by Ray.
- **Related systems:** Creative Studio; Creative Engine; Creative Execution
  Router; Asset Persistence Bot; Data Governor; Campaign Service; Model
  Manager; Systems; Supabase; Cloudflare.
- **Implementation:** `scripts/nexus_agent_platform/creative/r2_storage.py`,
  `scripts/nexus_agent_platform/creative/asset_persistence.py`, and the fixed
  authenticated asset-read route. The adapter fails closed if R2 or Supabase
  metadata access is not configured.
- **Implementation state:** IMPLEMENTED.
- **Configuration state:** The non-secret account ID and bucket are registered
  in the canonical Nexus runtime environment. The bucket-scoped S3 credential
  identity is registered in Nexus credential control and both secret
  components are configured in macOS Keychain. Secret values are not stored
  here.
- **Bucket:** `nexus-creative-assets`, Standard storage, created and listed via
  Wrangler 4.149.0 on 2026-11-17; location `WNAM`. `wrangler r2 bucket info`
  reports Standard storage. `wrangler r2 bucket domain list` returned no custom
  domains, and `wrangler r2 bucket dev-url get` reports public r2.dev access
  disabled. No public access was configured.
- **Wrangler bootstrap certification:** Bucket list, temporary object PUT, GET,
  SHA-256 comparison, and DELETE passed. Temporary object key:
  `certification/r2-bootstrap-test-a20a008ad5db4530a9705c94e020fbac.txt`; the
  object was deleted after verification. Bucket info subsequently reported
  zero objects and zero bytes.
- **Data Governor policy:** Exact-scope rows exist for
  `CLOUDFLARE_R2 / creative_canonical_storage`. Certification is limited to 10
  objects, 100 MiB aggregate uploads, 50 MiB per object, 50 Class A operations,
  100 Class B operations, 20 certification-only deletes, 300 seconds, 3
  retries, and a $0.10 estimated-cost ceiling. Normal Creative persistence
  remains `HUMAN_APPROVAL_REQUIRED` until a production budget is authorized.
  Bucket administration, public access, credential creation, and production
  deletion are not permitted.
- **Cost model:** Configured separately in
  `configs/nexus_r2_storage_cost_policy.json`. The estimate uses gross Standard
  rates ($0.015/GB-month, $4.50/million Class A, $0.36/million Class B, free
  egress) and does not subtract unknown remaining free-tier allowances.
  Estimate mode is `BOUNDED_ADVISORY`; source verified 2026-11-17.
- **Live certification state:** R2 and Asset Persistence Bot certification
  passed on 2026-11-17. Governed boto3 calls passed authenticated object HEAD,
  image/video PUT, bounded GET, downloaded-content SHA-256 comparison,
  short-lived signed-read URL generation, and deduplication. Asset Persistence
  Bot ingested an image and video to R2, verified each object, registered
  metadata in Supabase, linked both to the existing canary campaign
  `campaign-marketing-creative-canary-20261009-20042`, and recorded generation
  receipts. Test asset IDs:
  `r2cert_image_r2botcert-20261117-76d6efba6b` and
  `r2cert_video_r2botcert-20261117-76d6efba6b`. Generation receipts:
  `generation:r2botcert-20261117-76d6efba6b_image_dedup:f6095f3e92fb3e87` and
  `generation:r2botcert-20261117-76d6efba6b_video:9b65c2c2fe41c752`.
- **Certification object cleanup:** Test objects under
  `certification/r2-governor/r2cert-20261117-8bce6584477b/` and the linked
  canary assets remain in the private bucket. No approved delete verifier is
  configured, so no object deletion was attempted. Production deletion remains
  denied.
- **Creative Studio delivery:** Supabase asset metadata lookup and the
  governed short-lived R2 signed-read operation passed. The browser-authenticated
  Admin route was not exercised in this run; the existing `asset_signed_url`
  route requires an authenticated Admin session.
- **Supabase changes:** Two exact Data Governor policy scopes were provisioned
  or updated, and two canary Creative asset metadata records were registered.
  No media bytes were stored in Supabase.
- **Usage visibility:** Local registered-object and operation receipts provide
  bounded visibility. Account-wide Cloudflare usage and billing are not
  inferred.

## AGENT_CAPABILITY_CONTROL_PLANE

- **Status:** IMPLEMENTED / DENY-BY-DEFAULT REGISTRIES
- **Canonical identities:** `configs/nexus_agent_control_plane.json` registers the Nova company coordinator and named domain leads, plus bounded specialist microbots. `configs/nexus_skill_registry.json` is the skill identity registry; `configs/connector_registry.json` remains the connector registry; `configs/nexus_model_profile_registry.json` contains profile aliases only; `configs/nexus_execution_environment_registry.json` records execution/storage/data-plane environments and conservative certification state.
- **Enforcement:** `scripts/nexus_agent_platform/agent_control_plane.py` validates agent/bot skill, connector, model-profile, and environment permissions. It does not execute capabilities or expose credentials. Existing governed executors, credential control, Model Manager, Data Governor, and R2 Asset Persistence remain authorities.
- **Rules:** bots request model profiles only; Model Manager selects provider/model; execution router selects an explicitly allowed healthy environment; a registered identity is not proof of runtime availability; Nova has no raw R2 credential authority; Mercury has no live-trading authority; Alpha has no publishing authority; `AI_WORKER_CANNOT_TERMINATE_WORKFLOW` remains standing.
- **Runtime state:** Mac Research/API/MCP and bridge processes were observed on 2026-11-17. Host service presence is recorded separately from protocol certification. Contabo and Meta browser generation are not certified by this registry. R2 and Supabase preserve their already-authoritative storage/state roles.

## EXECUTION_ENVIRONMENT_REGISTRY

- **Status:** IMPLEMENTED; runtime claims are evidence-scoped.
- **Registry:** `configs/nexus_execution_environment_registry.json` includes Mac mini, Contabo candidate, Meta browser candidates, Modal, RunPod, Remotion, Codex build, Cloudflare R2, and Supabase. R2 is canonical storage, not compute; Supabase is the canonical metadata/business/workflow plane, not compute.
- **Routing rule:** only allowlisted environments with an active/live-certified status and healthy runtime evidence may be selected. Candidate, unavailable, or unverified environments cannot be routed as fallbacks unless a future certification updates their state.

## SKILL_CONNECTOR_MODEL_ENVIRONMENT_SEPARATION

- **Status:** IMPLEMENTED.
- Skills describe bounded work; connectors describe external/system interfaces; model profiles describe task classes; environments describe where work can execute. These registries are separate and joined by agent/bot policy.
- Actual provider/model selection stays in the existing Model Manager. Credentials stay behind Nexus credential authority. Hermes remains capability infrastructure and is not Nexus governance authority.

## CREATIVE_EXECUTION_ROUTING

- **Status:** EXISTING ROUTER REUSED; registry-backed control-plane policy added.
- Creative Intent and prompt-specialist identities are distinct from provider selection. Existing Creative Execution Router chooses location; Model Manager owns provider/model selection; Asset Persistence Bot remains deterministic and canonicalizes completed media to R2 with Supabase metadata. Unverified image/video/voice generators remain blocked rather than inferred active.
- **Nova placement:** `ORACLE_NOVA_HERMES` is registered separately from Mac Research. The approved resolver verified Oracle SSH authority, active Nova service, and running Hermes runtime on 2026-11-17. Process health is observed; MCP/tool protocol health was not tested here, so routing still requires a live health observation.
- **Hermes MCP certification:** On 2026-11-17 the approved Oracle resolver ran authenticated Hermes MCP initialization/discovery for Research (9 tools) and Nexus (154 tools). This certifies those MCP endpoints and tool discovery only; individual tool permissions remain governed by Nexus MCP policy, and this is not proof that every tool or model-generation capability is operational.

## NEXUS_WORKFLOW_FABRIC_R1

- **Status:** Implemented as controller and contracts; runtime activation remains bounded.
- **Controller:** `scripts/nexus_agent_platform/workflow_fabric.py` owns workflow lifecycle, step receipts, handoffs, bounded context packets, authorization preflight, retries/continuation, approval waits, owner cancellation, completion receipts, and idle-safe cronbot dispatch. AI worker outcomes cannot set workflow terminal state.
- **Persistence:** Workflow envelopes use the existing `nexus_durable_jobs.governance_context` JSONB and root job identity. The root row is scheduled far in the future and held in `WAITING`, so generic durable-job workers do not claim it. No new workflow table or migration was added.
- **Execution authorization:** Each step checks its registered domain agent, microbot, skill, connector status, model profile, and runtime-observed allowed environment through the existing Agent Control Plane and Model Manager. Missing handlers or unverified capabilities persist as continuation states; no default worker execution is provided.
- **Continuation:** Deterministic ordering supports same-worker retry, model/worker/environment fallback only when explicitly declared and available, partial preservation, dependency/approval waits, retry scheduling, and escalation. `FAILED_TERMINAL_SYSTEM` is reserved to controller policy and is never accepted from a worker.
- **n8n:** Existing Contabo n8n 2.45.6 passed authenticated bounded health and workflow-list reads (5 workflows) through its registered Keychain credential identity. Nexus outbound workflow connectivity and n8n persistence backend remain unverified. The adapter is read-only; no schedules or webhooks were activated.
- **Cronbots:** Six named cronbot contracts are registered as `REGISTERED_NOT_SCHEDULED`; idle checks make zero model calls. Dispatch handlers require runtime integration before schedule activation.
- **Approval and completion:** Approval waits persist at the blocked step and resume without resetting prior certified work. A workflow cannot become `COMPLETED` without all required step states and a deterministic completion receipt. Publishing, spending, external messaging, deployment, migration, and live trading remain approval gated.
- **First definition:** `configs/workflows/nexus_business_to_campaign_r1.json` defines the 15-step Research-to-Campaign path. Unverified competitive intelligence and campaign/creative transports remain explicit dependencies; no campaign was published or any media spend performed.
- **Integration contracts:** `configs/nexus_workflow_integrations.json` defines Research Room event references, certified-only measurement, competitive-intelligence source policy, and the Creative → R2 → Supabase asset chain. These are integration contracts, not claims that all producers are connected.

## NEXUS_WORKFLOW_FABRIC_RUNTIME_ACTIVATION_20261117

- **Status:** Partial runtime certification; Workflow Fabric remains bounded and the existing GoClear instance remains parked. This entry records observed evidence and does not certify untested capabilities.
- **Oracle/Hermes:** Approved Oracle resolver passed (`NOVA_SERVICE=ACTIVE`, `HERMES_RUNTIME=RUNNING`). Hermes `mcp test nexus_mcp_remote` passed authenticated connection and discovered 154 tools. This establishes MCP access/tool discovery (Level 2 capability evidence), not general tool execution. Codex OAuth reports logged in. Native Hermes skills, browser/computer use, web search/extract, delegate, messaging, cron, and model runtime canaries were not run; the resolver exposes no approved command for those operations.
- **Contabo:** Canonical `nexus-contabo` access identity resolved and read-only SSH inspection succeeded (Ubuntu 24.04.5, x86_64, 6 vCPU, 11 GiB RAM, 96 GiB disk). Docker and the existing n8n/REA containers were visible. The host has no Node or Playwright executable; the REA container has no Playwright/Selenium/Chromium runtime or browser listener. Computer-use is therefore unverified/unavailable through the inspected path. Overall Contabo certification remains Level 1; n8n read-only health/workflow-list evidence is Level 2 only for that capability.
- **Modal:** Existing `goclearonline` profile and deployed `nexus-creative-gpu-worker` / `nexus-remote-cpu-worker` app identities are visible. No function/job was launched because its governed execution route and cost preflight were not established. Modal remains Level 1 access verified; no GPU/artifact/R2 end-to-end certification is claimed.
- **Mac Research:** Fresh bounded probes on 2026-11-17 returned Research API HTTP 200, R10 HTTP 200, and Research MCP HTTP 401. The MCP challenge is an expected authentication requirement, not a protocol failure. The resolver-driven authenticated Hermes MCP test also discovered the Nexus MCP tool set. `scripts/nexus_agent_platform/workflow_runtime_health.py` now records bounded timestamped local endpoint health and rejects stale health observations before converting them to router status.
- **R2 and Supabase:** Retain their prior Level 4 certification from the existing Systems Ledger; no broad retest or mutation was performed in this activation pass.
- **Other environments:** Meta.ai Mac/Contabo, Google interactive surfaces, Gemini API model route, and Remotion render path were not canary-certified in this pass. No new provider/model or paid generation was invoked.
- **Workflow handlers and durable instance:** The existing GoClear workflow `wf_dfccb523f5114f68a53e226b4c33f402` remains `WAITING_DEPENDENCY` at `OBJECTIVE_INTAKE`, with no last certified step. A fresh read of the existing durable root confirms that the default controller has no runtime handlers bound. No duplicate workflow was created and no step was marked complete.
- **n8n and notifications:** Existing n8n 2.45.6 remains authenticated/read-only with five workflows visible from prior certification. The Nexus adapter is read-only; no outbound callback was run. Completion delivery and cron schedules remain inactive.
- **Next activation boundary:** Register real handlers that execute through their authorized environments, expose approved health adapters for Oracle/Contabo/Modal, then dispatch `OBJECTIVE_INTAKE` and `RESEARCH_PLAN` on the existing workflow ID. Do not advance the workflow with local stubs or bypass provider/Data Governor approvals.
