# Nexus Research — RLS & Storage Audit

**Generated**: 2026-07-04
**Status**: DRAFT — NOT APPROVED — NOT LIVE

---

## Current Supabase State

| Check | Status |
|-------|--------|
| Supabase client exists in Nexus Research | No |
| Supabase client exists in Alpha | No |
| Any live Supabase connection | No |
| Any RLS policies defined for Nexus | No |
| Any migrations applied | No |
| Any storage buckets created | No |

---

## RLS Requirements for Future Tables

### nexus_research_artifacts
```sql
ALTER TABLE nexus_research_artifacts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "tenant_isolation" ON nexus_research_artifacts
  USING (tenant_id = auth.uid());

CREATE POLICY "admin_bypass" ON nexus_research_artifacts
  USING (auth.role() = 'service_role');
```

### nexus_research_reviews
```sql
ALTER TABLE nexus_research_reviews ENABLE ROW LEVEL SECURITY;

CREATE POLICY "tenant_isolation" ON nexus_research_reviews
  USING (tenant_id = auth.uid());

CREATE POLICY "admin_bypass" ON nexus_research_reviews
  USING (auth.role() = 'service_role');
```

### goclear_readiness_internal_tests
```sql
ALTER TABLE goclear_readiness_internal_tests ENABLE ROW LEVEL SECURITY;

CREATE POLICY "tenant_isolation" ON goclear_readiness_internal_tests
  USING (tenant_id = auth.uid());

CREATE POLICY "admin_bypass" ON goclear_readiness_internal_tests
  USING (auth.role() = 'service_role');
```

### goclear_readiness_report_drafts
```sql
ALTER TABLE goclear_readiness_report_drafts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "tenant_isolation" ON goclear_readiness_report_drafts
  USING (tenant_id = auth.uid());

CREATE POLICY "admin_bypass" ON goclear_readiness_report_drafts
  USING (auth.role() = 'service_role');
```

### ray_review_research_queue
```sql
ALTER TABLE ray_review_research_queue ENABLE ROW LEVEL SECURITY;

CREATE POLICY "admin_only" ON ray_review_research_queue
  USING (auth.role() = 'service_role');
```

---

## Storage Requirements

- No file storage in initial integration
- All content as structured data (JSONB/text)
- Future: if file uploads needed, use Supabase Storage with RLS

---

## Storage Buckets (Future)

| Bucket | Purpose | Access |
|--------|---------|--------|
| nexus-research-artifacts | Seed artifact files | admin-only |
| nexus-research-reports | Generated reports | admin-only |
| nexus-readiness-drafts | Readiness report drafts | admin-only |

---

## Audit Checklist Before Live Use

- [ ] All RLS policies tested
- [ ] Tenant isolation verified
- [ ] Admin bypass verified
- [ ] No anonymous access possible
- [ ] No public access possible
- [ ] Service role key never exposed to client
- [ ] All writes logged
- [ ] Rollback tested
