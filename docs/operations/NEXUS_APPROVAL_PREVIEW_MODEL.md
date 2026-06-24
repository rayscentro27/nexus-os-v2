# Nexus Approval Preview Model

Date: 2026-06-24

## Purpose

Approval cards must show Ray what he is approving before he clicks Approve, Reject, or Request changes. The approval row is still the decision gate; preview metadata is only for review.

Approving an approval must not publish, send, trade, deploy, start a scheduler, or set `publish_enabled=true` unless a separate gated runner explicitly performs that later.

## Current Preview Sources

The UI builds previews from:

- `approvals.title`
- `approvals.summary`
- `approvals.item_type`
- `approvals.item_id`
- `approvals.payload`
- linked `social_posts` rows where `social_posts.approval_id = approvals.id`
- linked `publish_readiness_packages` rows where `publish_readiness_packages.id = approvals.item_id`

## Recommended Metadata Shape

Future approval payloads should use this shape when possible:

```json
{
  "asset_type": "facebook_post",
  "preview_url": "https://...",
  "asset_url": "https://...",
  "thumbnail_url": "https://...",
  "image_url": "https://...",
  "video_url": "https://...",
  "caption": "Public-facing caption or script",
  "body": "Long body copy",
  "platform": "facebook",
  "target_account": "Clear Credentials",
  "cta_url": "https://nexusv20.netlify.app/goclear-apex-readiness.html",
  "landing_page_url": "https://nexusv20.netlify.app/goclear-apex-readiness.html",
  "package_type": "manual_publish_package",
  "package_path": "reports/manual_publish/package.json",
  "content_blocks": [],
  "sensitivity": "internal_summary",
  "requires_approval": true,
  "forbidden_actions": ["publish", "send", "trade", "deploy", "set_publish_enabled"]
}
```

## Preview Field Rules

Allowed in UI/Hermes review:

- approval id
- title
- item type
- status
- lane
- safe summary
- created time
- platform
- target account label/id
- caption/copy/body/text
- CTA/link
- landing page URL
- image/video/thumbnail/asset preview URL
- package copy
- compliance/risk notes
- score summary

Forbidden:

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

## Missing Data Behavior

If no preview copy/link/media exists, the UI shows `Preview not available` and lists the missing safe fields. The card must never crash or infer private data.

## Current Preview Types

- Social post approvals: copy, platform, target account, CTA/link when present.
- Manual publish packages: full package copy from `publish_readiness_packages`, CTA, platform, compliance status.
- Landing page approvals/enablement: public landing page preview link.
- Image/video approvals: inline image/video if a safe URL exists; otherwise open-preview link.
- Generic creative approvals: payload caption/body/CTA/risk/score.
