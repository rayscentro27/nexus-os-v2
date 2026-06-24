# Nexus Approval Preview and Hermes Review Report

Date: 2026-06-24

## What changed

Approval cards now show structured preview sections instead of only text metadata.

Hermes Command Center can now review pending approvals through a read-only, sanitized approval review helper.

## Files changed

- `src/lib/approvalReview.ts`
- `src/lib/hermesIntent.ts`
- `src/components/sections.tsx`
- `docs/operations/NEXUS_APPROVAL_PREVIEW_MODEL.md`
- `docs/operations/NEXUS_HERMES_APPROVAL_REVIEW.md`
- `reports/manual_publish/nexus_approval_preview_and_hermes_review_latest.md`

## Approval preview types now supported

- Social posts: caption/copy, platform, target account, CTA/link, media URL if present.
- Images: inline image when a safe image URL exists.
- Videos: inline player when a safe video URL exists; otherwise open-preview link.
- Landing pages: open landing page preview button/link.
- Manual publish packages: package type, full final post copy, CTA, platform, compliance status, risk flags.
- Generic creative approvals: caption/body, hook/CTA, score summary, compliance notes.

## Preview fields used

- `approvals.payload.caption`
- `approvals.payload.body`
- `approvals.payload.copy`
- `approvals.payload.text`
- `approvals.payload.preview_url`
- `approvals.payload.asset_url`
- `approvals.payload.image_url`
- `approvals.payload.video_url`
- `approvals.payload.thumbnail_url`
- `approvals.payload.landing_page_url`
- `approvals.payload.cta`
- `approvals.payload.platform`
- `approvals.payload.account_name`
- `approvals.payload.account_id`
- linked `social_posts.content`
- linked `social_posts.media_url`
- linked `publish_readiness_packages.final_post_copy`
- linked `publish_readiness_packages.cta`
- linked `publish_readiness_packages.compliance_status`
- linked `publish_readiness_packages.risk_flags`

## Approvals still lacking preview data

Approvals without caption/body/link/media/package data show `Preview not available` and list missing fields. The known `facebook_publish_enablement` approval has a safe landing page preview link but still needs the exact final post copy before Ray should approve enabling `publish_enabled`.

## Hermes safe read path

Hermes review uses:

`src/lib/approvalReview.ts`

It reads through the authenticated browser Supabase client and existing RLS. It does not use service-role keys and does not query from the Edge Function.

## Fields returned to Hermes

- id
- title
- item type
- status
- lane
- safe summary
- created time
- platform
- target account label/id
- caption/copy/body
- CTA/link
- public landing page URL
- preview/media URL
- package copy
- compliance/risk notes
- score summary
- recommendation

## Forbidden/sanitized fields

Forbidden fields include tokens, service-role keys, passwords, reset tokens, SSNs, credit reports, bank docs, tax docs, raw customer files, secrets, and private API payloads. The helper allowlists preview keys and drops sensitive-looking text.

## Example Hermes approval review response

```text
You have 1 pending approval visible. I can review it, but I cannot approve, reject, publish, send, trade, or set publish_enabled.

1. Enable one Facebook GoClear/Apex test post
Type: facebook_publish_enablement
Status: pending
Target: facebook · Clear Credentials
Summary: Token is valid and publish scopes exist. Approval is required before setting social_accounts.publish_enabled=true for one compliant GoClear/Apex test post.
Preview: https://nexusv20.netlify.app/goclear-apex-readiness.html
Risk: No ads, no boost, one-post limit.
Recommendation: Approve only after confirming the exact post copy and landing page.
Next action: Review it in the Approvals tab.
```

## Safety boundaries

- Hermes review is read-only.
- Hermes cannot approve or reject records.
- Hermes cannot publish.
- Hermes cannot send email.
- Hermes cannot trade.
- Hermes cannot deploy.
- Hermes cannot start a scheduler.
- Hermes cannot set `publish_enabled=true`.
