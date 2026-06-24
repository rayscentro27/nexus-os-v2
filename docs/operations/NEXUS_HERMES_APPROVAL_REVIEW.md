# Hermes Approval Review

Date: 2026-06-24

## Purpose

Hermes can help Ray review pending approvals in plain English without executing any approval decision.

Supported prompts include:

- `do I have approvals waiting`
- `review my approvals`
- `walk me through approvals one by one`
- `show me approval 13eafcab`
- `review #1`
- `what should I approve`
- `approval queue`

## Data Path

Hermes approval review runs in the authenticated frontend session using the Supabase anon client and existing RLS. It calls the shared approval review helper:

`src/lib/approvalReview.ts`

The helper reads pending approvals and linked preview records through admin-gated RLS:

- `approvals`
- `social_posts`
- `publish_readiness_packages`

This path is read-only. It does not call a worker and does not use the service-role key.

## Fields Hermes Receives

Hermes receives sanitized `internal_summary` approval review fields:

- id
- title
- item type
- status
- lane
- summary
- created time
- platform
- target account label/id
- caption/copy/body
- CTA/link
- public landing page URL
- image/video/thumbnail/asset preview URL
- package copy
- compliance/risk notes
- score summary
- recommendation

## Forbidden Fields

Hermes approval review never receives:

- access tokens
- service-role keys
- API keys
- passwords
- reset tokens
- SSNs
- credit reports
- bank docs
- tax docs
- raw customer files
- private API payloads

## Execution Boundary

Hermes may recommend Approve, Reject, or Request changes, but it cannot perform those actions.

If Ray says `approve #1`, Hermes responds that approval decisions must be made in the Approvals tab. Hermes does not update `approvals.status`, set `publish_enabled`, publish, send, trade, deploy, or start a scheduler.

## Example Response

```text
You have 3 pending approvals visible. I can review them, but I cannot approve, reject, publish, send, trade, or set publish_enabled.

1. Enable one Facebook GoClear/Apex test post
Type: facebook_publish_enablement
Status: pending
Target: facebook · Clear Credentials
Summary: Approval is required before enabling publish_enabled=true for one compliant GoClear/Apex test post.
Preview: https://nexusv20.netlify.app/goclear-apex-readiness.html
Risk: no ads; no boost; one post only
Recommendation: Approve only after confirming the exact post copy and live landing page.
Next action: Review it in the Approvals tab.
```
