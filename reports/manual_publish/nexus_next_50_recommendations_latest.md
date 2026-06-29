# Nexus Next 50 Recommendations

## 1. Activate Supabase core tables and RLS

- priority: P0 immediate
- impact: backend/data
- effort: large
- status: needs_Ray_approval
- next: Review the draft migration, test tenant policies locally, and approve a timestamped migration.

## 2. Replace demo client data with tenant-safe records

- priority: P0 immediate
- impact: client experience
- effort: large
- status: schedule
- next: Implement tenant membership and client profile reads after RLS passes.

## 3. Activate real YouTube metadata or transcript intake

- priority: P0 immediate
- impact: automation
- effort: small
- status: needs_Ray_approval
- next: Add YOUTUBE_API_KEY server-side or one approved transcript file, then rerun intake.

## 4. Approve the $97 payment and CRM path

- priority: P0 immediate
- impact: revenue
- effort: medium
- status: needs_Ray_approval
- next: Approve Stripe test mode, the $97 product/price, webhook mapping, and Supabase client creation.

## 5. Process today's prioritized Ray Review queue

- priority: P0 immediate
- impact: operations
- effort: small
- status: needs_Ray_approval
- next: Record approve/reject/defer for the same-day cards in priority order.

## 6. Build private document storage and message policies

- priority: P0 immediate
- impact: safety/compliance
- effort: large
- status: schedule
- next: Create private bucket, retention rules, malware scanning, consent, and tenant/client RLS tests.

## 7. Move dispute proof to synthetic sandbox testing

- priority: P1 high
- impact: safety/compliance
- effort: medium
- status: needs_Ray_approval
- next: Approve non-deliverable sandbox recipients and proof-only vendor tests; keep production disabled.

## 8. Validate the Meta connector read-only

- priority: P1 high
- impact: automation
- effort: small
- status: needs_Ray_approval
- next: Approve a token-redacted /me/accounts identity check; do not post.

## 9. Confirm the bounded continuous loop

- priority: P1 high
- impact: operations
- effort: small
- status: do_now
- next: Monitor nexus_today_ops heartbeat and stop it after eight cycles or earlier if needed.

## 10. Complete report-backed Hermes and Nexus Guide reads

- priority: P1 high
- impact: UI/UX
- effort: medium
- status: schedule
- next: Connect structured approved guidance and engine status after tenant-safe reads exist.

## 11. Seed tenant memberships with a synthetic local test user

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Seed tenant memberships with a synthetic local test user.

## 12. Write automated RLS cross-tenant denial tests

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Write automated RLS cross-tenant denial tests.

## 13. Map every remaining Supabase-ready export

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Map every remaining Supabase-ready export.

## 14. Add idempotency keys to future insert operations

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Add idempotency keys to future insert operations.

## 15. Create private storage retention schedule

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Create private storage retention schedule.

## 16. Define client document consent language

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Define client document consent language.

## 17. Add malware scanning design for uploads

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Add malware scanning design for uploads.

## 18. Create payment webhook signature verification

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Create payment webhook signature verification.

## 19. Create idempotent post-payment client creation

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Create idempotent post-payment client creation.

## 20. Write the $97 fulfillment service-level checklist

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Write the $97 fulfillment service-level checklist.

## 21. Approve $97 landing-page claims

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Approve $97 landing-page claims.

## 22. Create the sales conversation script

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Create the sales conversation script.

## 23. Build subscription upgrade event records

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Build subscription upgrade event records.

## 24. Create referral tracking records

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Create referral tracking records.

## 25. Validate Stripe price identifiers in test mode

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Validate Stripe price identifiers in test mode.

## 26. Add payment failure recovery tasks

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Add payment failure recovery tasks.

## 27. Create CRM lead-to-client state transitions

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Create CRM lead-to-client state transitions.

## 28. Add client auth role routing

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Add client auth role routing.

## 29. Hide demo labels automatically for authenticated clients

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Hide demo labels automatically for authenticated clients.

## 30. Create client data loading/error states

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Create client data loading/error states.

## 31. Add readiness score versioning

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Add readiness score versioning.

## 32. Add score explanation audit history

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Add score explanation audit history.

## 33. Create guidance approval expiry

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Create guidance approval expiry.

## 34. Add client question escalation notifications

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Add client question escalation notifications.

## 35. Create GoClear review turnaround states

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Create GoClear review turnaround states.

## 36. Add dispute evidence completeness scoring

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Add dispute evidence completeness scoring.

## 37. Create dispute letter version history

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Create dispute letter version history.

## 38. Define certified-mail sandbox vendor criteria

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Define certified-mail sandbox vendor criteria.

## 39. Add connector credential rotation checklist

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Add connector credential rotation checklist.

## 40. Validate Meta token expiry read-only

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Validate Meta token expiry read-only.

## 41. Create social post version history

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Create social post version history.

## 42. Create content compliance linting

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Create content compliance linting.

## 43. Add YouTube source provenance fields

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Add YouTube source provenance fields.

## 44. Create transcript consent/provenance checklist

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Create transcript consent/provenance checklist.

## 45. Add bounded YouTube quota policy

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Add bounded YouTube quota policy.

## 46. Schedule connector health checks without external actions

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Schedule connector health checks without external actions.

## 47. Add engine-run correlation IDs

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Add engine-run correlation IDs.

## 48. Add proof-event retention policy

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Add proof-event retention policy.

## 49. Create operational failure alerts

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Create operational failure alerts.

## 50. Document tmux loop recovery

- priority: P2 medium
- impact: operations
- effort: medium
- status: schedule
- next: Implement and verify: Document tmux loop recovery.
