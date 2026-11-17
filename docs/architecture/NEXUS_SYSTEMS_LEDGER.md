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
