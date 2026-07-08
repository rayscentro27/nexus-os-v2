# Repo Discovery Report

**Generated:** 2026-07-07  
**Primary Repo:** ~/nexus-os-v2 (commit 8d61ec5)

## Repos Found

| Repo | Exists | Supabase Config | Client Portal Migrations | Stripe/Resend Refs |
|------|--------|-----------------|-------------------------|-------------------|
| ~/nexus-os-v2 | Yes (PRIMARY) | Yes | Yes (20260629095450, 20260706120000, 20260707120000) | Yes |
| ~/nexus-ai | Yes | Yes (legacy) | No (older migrations) | No |
| ~/nexuslive | Yes | Yes (legacy) | No (older migrations) | No |
| ~/nexus-ai-council-sandbox | Yes | No | No | No |
| ~/nexus | No | - | - | - |

## Key Findings

- **Primary source of truth:** ~/nexus-os-v2
- Legacy repos contain older Supabase migrations (pre-client-portal)
- No Stripe/Resend/Social references found in legacy repos
- Legacy repos have .env files with some overlapping keys
- Migration 20260629095450 exists only in ~/nexus-os-v2

## Conflicts

- None identified. Legacy repos are not used for client portal.
