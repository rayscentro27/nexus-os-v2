# Nexus Research — Supabase Connection Plan

**Generated**: 2026-07-04
**Status**: DRAFT — NOT APPROVED — NOT LIVE

---

## Purpose

This plan defines how Nexus Research and GoClear Readiness outputs would integrate with Supabase in the future. No live writes are performed. No migrations are applied. This is a design document for Ray Review.

---

## What Should Be Stored Later

| Data Type | Table | Rationale |
|----------|-------|-----------|
| Research artifacts | nexus_research_artifacts | Track ingested seed artifacts with provenance |
| Adapter processing results | nexus_research_reviews | Track admin notes and Ray Review drafts |
| Internal test profiles | goclear_readiness_internal_tests | Track hypothetical test profile runs |
| Readiness report drafts | goclear_readiness_report_drafts | Track generated readiness reports |
| Ray Review queue items | ray_review_research_queue | Track items awaiting Ray approval |
| Supabase integration audit log | nexus_supabase_audit_log | Track all future Supabase operations |

---

## What Should Remain Local

| Data Type | Reason |
|----------|--------|
| Hypothetical test profiles | Test-only, no value in Supabase |
| Local output files | Internal workflow artifacts |
| Builder intermediate data | No persistence needed |
| Fixture files | Test infrastructure |

---

## What Should Never Be Stored

| Data Type | Reason |
|----------|--------|
| Real client PII | Until security workflow approved |
| Service role keys | Never store secrets |
| API keys | Never store secrets |
| Passwords | Never store secrets |
| Credit report data | Until compliance approved |
| Financial account numbers | Until security approved |

---

## Existing Tables That Might Be Reuseable

Search the repo for existing Supabase schema. Based on codebase analysis:

- No existing Nexus Research tables found
- No existing GoClear readiness tables found
- Alpha research adapter uses local-only storage
- No Supabase client code exists in Nexus Research

---

## tenant_id Requirements

All Nexus Research Supabase tables should include:
- `tenant_id UUID NOT NULL REFERENCES auth.users(id)`
- RLS policy: users can only access their own tenant's data
- Admin users bypass tenant isolation with service role

---

## Admin-Only Access

- All Nexus Research data is admin-only until Ray Review approval
- Service role required for admin operations
- Row-Level Security must enforce admin-only access
- No anonymous access allowed

---

## Ray Review Approval State

Each record should track:
- `ray_review_status: 'pending' | 'approved' | 'rejected'`
- `ray_reviewed_at: timestamp | null`
- `ray_reviewed_by: uuid | null`
- `client_facing_allowed: boolean DEFAULT false`

---

## Draft vs Approved State

- All outputs start as `draft`
- Ray Review changes status to `approved` or `rejected`
- Only `approved` outputs can become client-facing
- Draft outputs remain admin-only

---

## Source Artifact Hash/Provenance

Each stored record should include:
- `source_artifact_id: text` — references nexus_research artifact
- `source_sha256: text` — hash of source content
- `adapter_version: text` — version of adapter that processed it
- `processed_at: timestamp` — when adapter processed it

---

## RLS Requirements

- All tables require RLS enabled
- Default policy: tenant isolation
- Admin policy: service role bypass
- No anonymous read/write access
- No public access

---

## Storage Requirements

- No file uploads in initial integration
- All data stored as structured JSON/JSONB
- Markdown content stored as text
- Timestamps in UTC
- UUIDs for primary keys

---

## Audit Log Requirements

All Supabase writes should log:
- Operation type (insert/update/delete)
- Table affected
- Record ID
- User ID
- Timestamp
- Source (adapter/builder/admin)

---

## Rollback Strategy

- Each migration has a down migration
- Backup before each migration
- Test rollback on staging before production
- Document rollback steps for each migration
