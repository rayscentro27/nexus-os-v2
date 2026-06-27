# Nexus Affiliate Approval Waiting Room + Partner URL Intake + First Offer Launch Gate

Builds on the partner offer launch readiness work (commit 5075705) without duplicating
`partnerOffers`, pricing validation, launch cards, the payment contract, or `LaunchReadinessCard`.

## Affiliate Approval Waiting Room

`src/config/affiliateApprovalStatus.ts` tracks each non-free partner program through an approval
lifecycle: `not_applied → application_submitted → pending_review → approved` (or `rejected` /
`on_hold`), plus a `url_intake_status` (`awaiting_urls → urls_received → urls_validated`). Defaults to
`not_applied`. `APPROVAL_PRIORITY` orders pursuit (SmartCredit → Bluevine → DocuPost → …).
Report: `scripts/partners/generate_affiliate_waiting_room_report.py` →
`reports/manual_publish/affiliate_waiting_room_latest.md`.

## Partner URL Intake (safe)

`src/lib/partnerUrlIntake.ts` validates approved partner URLs **without navigating to, activating, or
fetching** them: HTTPS-only, no unsafe schemes/characters, must have a real host, rejects
`placeholder.invalid`. An intake is accepted only with a valid URL **and** a disclosure **and** a DIY
option. `projectedConfig()` shows what an offer's config status would become — immutably, never
mutating the registry. Tool: `scripts/partners/intake_partner_urls.py --dry-run --json`
(`--intake-file <json>` optional; built-in dev self-test sample is not persisted and not real).

## Disclosure + DIY verification

`scripts/partners/verify_partner_disclosures_and_diy.py` asserts every offer has a disclosure (or is
free/official) and a DIY/free option.

## First Offer Launch Gate

`src/lib/firstOfferLaunchGate.ts` is a go/no-go gate for the $97 Readiness Review. It **never
launches, publishes, charges, or connects payment** — it reports `can_launch` and the exact blockers.
Defaults to `can_launch=false` (fails closed): Ray must approve the offer + copy, and payment is a
separate explicitly-approved step. Report: `scripts/revenue/generate_first_offer_launch_gate.py`.

## Command Center

`AffiliateWaitingRoomCard` (separate from `LaunchReadinessCard`) shows approval counts, URLs awaited,
and the $97 launch gate status.

## Safety

Nothing here publishes, sends, charges, creates payment links, activates Stripe/connectors, contacts
clients/partners, submits applications, connects the Client Vault, or uses real client data. Partner
URLs are validated strings only. Everything remains approval-gated and internal.
