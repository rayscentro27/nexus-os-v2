# Nexus Research — Table Mapping Plan

**Generated**: 2026-07-04
**Status**: DRAFT — NOT APPROVED — NOT LIVE

---

## Proposed Tables

### 1. nexus_research_artifacts

Stores ingested Nexus Research seed artifacts.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | uuid | PK DEFAULT gen_random_uuid() | Record ID |
| tenant_id | uuid | NOT NULL REFERENCES auth.users(id) | Tenant isolation |
| artifact_id | text | NOT NULL UNIQUE | Nexus artifact ID (e.g., nexus-res-20260704-001) |
| category | text | NOT NULL | Artifact category |
| filename | text | NOT NULL | Source filename |
| source_path | text | NOT NULL | Relative source path |
| sha256 | text | NOT NULL | Content hash |
| title | text | NOT NULL | Artifact title |
| short_summary | text | | Brief summary |
| evidence_quality | text | NOT NULL | verified/credible/unverified/demo/opinion |
| compliance_flags | jsonb | DEFAULT '[]' | Compliance flags |
| guarantee_flags | jsonb | DEFAULT '[]' | Guarantee flags |
| safety_status | text | NOT NULL | safe/flagged/blocked |
| admin_only | boolean | NOT NULL DEFAULT true | Admin-only flag |
| ray_review_status | text | NOT NULL DEFAULT 'pending' | pending/approved/rejected |
| client_facing_allowed | boolean | NOT NULL DEFAULT false | Client-facing flag |
| source_sha256 | text | NOT NULL | Hash of original content |
| adapter_version | text | NOT NULL | Adapter version used |
| ingested_at | timestamptz | NOT NULL DEFAULT now() | Ingestion timestamp |
| created_at | timestamptz | NOT NULL DEFAULT now() | Record creation |
| updated_at | timestamptz | NOT NULL DEFAULT now() | Last update |

### 2. nexus_research_reviews

Stores adapter-generated admin notes and Ray Review drafts.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | uuid | PK DEFAULT gen_random_uuid() | Record ID |
| tenant_id | uuid | NOT NULL REFERENCES auth.users(id) | Tenant isolation |
| artifact_id | text | NOT NULL | References nexus_research_artifacts |
| review_type | text | NOT NULL | admin_note / ray_review_draft |
| content | jsonb | NOT NULL | Review content |
| ray_review_status | text | NOT NULL DEFAULT 'pending' | pending/approved/rejected |
| client_facing_allowed | boolean | NOT NULL DEFAULT false | Client-facing flag |
| created_at | timestamptz | NOT NULL DEFAULT now() | Record creation |
| updated_at | timestamptz | NOT NULL DEFAULT now() | Last update |

### 3. goclear_readiness_internal_tests

Stores internal test runner results.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | uuid | PK DEFAULT gen_random_uuid() | Record ID |
| tenant_id | uuid | NOT NULL REFERENCES auth.users(id) | Tenant isolation |
| profile_id | text | NOT NULL | Test profile ID (e.g., TEST-001) |
| profile_label | text | NOT NULL | Profile label |
| profile_data | jsonb | NOT NULL | Hypothetical profile data |
| scorecard | jsonb | NOT NULL | Readiness scorecard |
| categories_used | jsonb | NOT NULL | Categories used |
| generated_at | timestamptz | NOT NULL | When test was run |
| created_at | timestamptz | NOT NULL DEFAULT now() | Record creation |

### 4. goclear_readiness_report_drafts

Stores generated readiness report drafts.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | uuid | PK DEFAULT gen_random_uuid() | Record ID |
| tenant_id | uuid | NOT NULL REFERENCES auth.users(id) | Tenant isolation |
| test_id | uuid | NOT NULL | References goclear_readiness_internal_tests |
| profile_id | text | NOT NULL | Test profile ID |
| report_data | jsonb | NOT NULL | Full report data |
| report_label | text | NOT NULL | Report label |
| ray_review_status | text | NOT NULL DEFAULT 'pending' | pending/approved/rejected |
| client_facing_allowed | boolean | NOT NULL DEFAULT false | Client-facing flag |
| created_at | timestamptz | NOT NULL DEFAULT now() | Record creation |
| updated_at | timestamptz | NOT NULL DEFAULT now() | Last update |

### 5. ray_review_research_queue

Stores items awaiting Ray Review.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | uuid | PK DEFAULT gen_random_uuid() | Record ID |
| item_type | text | NOT NULL | artifact/review/test/report |
| item_id | uuid | NOT NULL | Reference to source record |
| status | text | NOT NULL DEFAULT 'pending' | pending/approved/rejected |
| ray_notes | text | | Ray's review notes |
| reviewed_at | timestamptz | | When reviewed |
| created_at | timestamptz | NOT NULL DEFAULT now() | Record creation |

---

## Migration Draft Location

Migrations should be created in:
`reports/nexus_research/supabase_plan/draft_migrations/`

Do not apply until approved by Ray.
