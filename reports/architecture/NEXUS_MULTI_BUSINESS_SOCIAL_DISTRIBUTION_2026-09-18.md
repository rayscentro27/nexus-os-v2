# Nexus Multi-Business Social Distribution

Status: `PASS_REAL_BOUNDED_PREPUBLISH`

## Scope

This implementation adds one provider-neutral, draft-only distribution router.
It is deliberately stopped before scheduling or live publication.  It reuses
the existing social draft engine, approval lane, content policy, creative
campaign records, compliance receipts, and legacy Supabase social tables.  It
does not create a second publisher or credential store.

## Existing architecture audit

| Capability | Finding | Classification |
|---|---|---|
| Social Draft Engine | Internal captions/hooks/hashtags and approval cards | PASS_REAL |
| Social connector health | Meta configuration status record; last proof was not network validated | PARTIAL_REAL |
| Social publish gate | Explicitly closed; public posting disabled | PASS_REAL_BOUNDED |
| Facebook publisher | Legacy dry-run/real path exists, but is outside this task and remains unused | CODE_PRESENT_NOT_PROVEN_FOR_CANONICAL_ROUTER |
| Instagram/Facebook seed records | Public IDs and environment-variable names only; no tenant/brand mapping | PARTIAL_REAL_AMBIGUOUS |
| Social analytics | Generic event/outcome analytics and connector records exist | PARTIAL_REAL |
| Attribution | Existing campaign/variant/UTM concepts; canonical social projection added here | PARTIAL_REAL |
| Duplicate social registry | None found before this implementation | NOT_FOUND |

The current shell has no Meta credential variables present.  The repository
contains historical connector configuration indicating a Meta connector, but
that is not proof of an authenticated account in this runtime.  The legacy
Facebook/Instagram rows therefore remain `UNKNOWN_UNPROVEN` for business and
brand ownership and are not promoted into the canonical registry.

## Canonical contracts

`SocialAccount` is the only account record consumed by the router.  It carries
tenant, business, brand, platform, status, capability flags, and a credential
reference only.  Raw credentials are never stored in the record.

`SocialAccountRegistry` provides account lookup, business/brand filtering,
scope validation, readiness filtering, and non-secret health projection.

`SocialDistributionRequest` binds campaign, variant, creative assets, target
platforms, target account IDs, compliance receipt, approval reference,
attribution, and `publish_mode`.  Only `DRAFT_ONLY` is accepted by this task.

`SocialPost` is the canonical future post state record.  Queue states are
`WAITING_CREATIVE`, `WAITING_COMPLIANCE`, `WAITING_APPROVAL`, `READY`,
`SCHEDULED`, `PUBLISHED`, and `BLOCKED`.

The `SocialPlatformAdapter` interface exposes `probe`, account health, draft
preparation/validation, status, and analytics methods.  Its schedule/publish
operations are represented but not called.

## Isolation policy

The router performs code-level equality checks, not prompt-level checks:

* request tenant must equal account tenant;
* request business must equal account business;
* request brand must equal account brand;
* account platform must be one of the request targets;
* assets with known brand metadata must match the request brand.

Cross-platform distribution is allowed for accounts belonging to the same
business and brand.  Cross-business and cross-brand distribution is blocked by
default.  No override is active; a future override would require explicit
source/destination, reason, approval, expiry, compliance review, and receipt.

## GoClear fixture and pre-publish proof

The existing restaurant/funding-readiness campaign fixture is:

* campaign: `goclear-funding-readiness-r20b`
* offer: `readiness_review_97`
* variant: `restaurant-transformation-internal-v1`
* landing domain: `goclearonline.cc`
* message: readiness and clearer next steps, not guaranteed approval/funding

Two legacy metadata candidates are visible in the repository seed (`Clear
Credentials` Facebook and `GoClearOnline` Instagram), but neither is
authenticated in the current runtime and neither carries a canonical
tenant/business/brand mapping.  They are therefore `UNKNOWN_UNPROVEN`, not
`READY` GoClear accounts.  Synthetic `TEST` accounts were used only in unit
certification, never as production account claims.

The matching-account path produces platform-specific draft packages and a
`READY_FOR_REVIEW` result only when compliance and approval references are
explicitly supplied to the test harness.  The real campaign approval remains
`PENDING_RAY_REVIEW`, so the live campaign is truthfully `WAITING_APPROVAL` /
`BLOCKED_ACCOUNT_CONFIGURATION`, not publish-ready.

Platform packages are distinct: Instagram uses vertical creative, caption,
hashtags and link strategy; Facebook uses headline/caption/link packaging;
YouTube Shorts uses title/description/short-form CTA; LinkedIn uses business
copy/link packaging.  No package is sent to a platform.

## Compliance, approval, and attribution

The router requires an approved compliance receipt and approved publication
approval for a `READY_FOR_REVIEW` draft package.  Missing either produces a
specific block.  Publication approval is not granted in this certification.

Attribution includes business, brand, campaign, variant, creative, platform,
social account, and available UTM fields.  No live post ID or live metric is
fabricated.  Future analytics feed Marketing, Research, Alpha, and Creative
through the existing governed outcome/feedback paths.

## Account creation and health

`SocialAccountProvisioningRequest` and `SocialAccountReadiness` define a future
account-preparation contract.  Account creation itself is not executed.  CAPTCHA,
SMS/2FA, identity/business verification, and terms requiring human confirmation
remain human boundaries.

Health reports configured/authenticated/read/publish/analytics state without
exposing secrets.  The current real inventory is:

* Meta connector record: configured in historical repository state, publish
  disabled, not network validated in the current run;
* Facebook/Instagram seed IDs: two metadata candidates present but canonical
  ownership mapping unknown;
* current Meta environment credentials: absent;
* GoClear canonical accounts: `0 READY/PROVEN` (2 legacy metadata candidates);
* YouTube API/research records are research sources, not treated as a YouTube
  publishing account.

## Certification cases

| Case | Result |
|---|---|
| A matching GoClear account | Synthetic same-business draft path `READY_FOR_REVIEW`; real path blocked by account configuration/approval |
| B wrong business account | `POST_BLOCKED_CROSS_TENANT` / cross-business scope block |
| C missing compliance approval | `POST_BLOCKED_COMPLIANCE` |
| D missing Ray publication approval | `POST_BLOCKED_APPROVAL` |
| E wrong-brand asset | `POST_BLOCKED_CROSS_BRAND_ASSET` |
| F unknown/unhealthy account | `POST_BLOCKED_UNKNOWN_ACCOUNT` / `POST_BLOCKED_ACCOUNT_NOT_READY` |
| G same-business multi-platform | Synthetic Instagram + Facebook draft packages pass without publication |
| H future synthetic business | Cross-business selection blocked |

## Safety boundary and remaining work

`SOCIAL_PUBLICATION=NO`, `SOCIAL_ACCOUNT_MUTATION=NO`, `CUSTOMER_CONTACT=NO`,
and `MONEY_SPENT=NO`.  No tokens, customer data, or public post IDs are in the
module, report, or tests.

Remaining blockers are external/configuration boundaries: establish an
approved tenant/business/brand mapping for any real social account, reauthorize
the required provider credential through the existing credential path, and
obtain Ray approval for a precisely scoped future publication.  The next
machine action is to register a verified account through the canonical registry
and run another draft-only certification; publication remains a separate task.
