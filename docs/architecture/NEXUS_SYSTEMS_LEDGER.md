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
- **Live certification state:** PARTIAL. The governed boto3 path passed
  authenticated object HEAD, image and video PUT/HEAD/GET, fetched-content hash
  verification, signed-read URL generation, and repeat-ingestion deduplication
  on 2026-11-17. The private test objects are retained under
  `certification/r2-governor/r2cert-20261117-8bce6584477b/`; the current
  adapter has no authorized certification-delete verifier, so it did not
  attempt deletion. Full Asset Persistence Bot completion and Creative Studio
  delivery remain uncertified because the canonical Creative metadata store is
  not configured (`metadata_store_configured() = false`); no asset metadata
  rows were written. Supabase contains only the exact R2 Governor policy rows
  created/updated for certification and approval-gated production.
- **Usage visibility:** Local registered-object and operation receipts provide
  bounded visibility. Account-wide Cloudflare usage and billing are not
  inferred.
