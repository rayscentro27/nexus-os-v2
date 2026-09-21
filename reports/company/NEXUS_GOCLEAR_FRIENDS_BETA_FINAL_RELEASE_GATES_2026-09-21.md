# NEXUS GoClear Friends-Beta Final Release Gates — 2026-09-21

Evidence rule: all records used here are synthetic controlled identities. No real customer data, bulk email, paid ads, spend, or public social publishing was used. Existing GoClear, Supabase, Marketing Distribution, Resend, and queue semantics were reused.

## === FOLLOW-UP ===

FOLLOWUP_TRIGGER_EVENT=review_requested

FOLLOWUP_TRIGGER_IMPLEMENTATION=review-request RPC inserts one `goclear_followup_jobs` work item; the client adapter automatically invokes the existing Supabase follow-up worker after the lifecycle event. The worker writes the canonical Marketing Distribution email/message records, sends through Resend, and updates the job receipt.

FOLLOWUP_TRIGGER_WORK_ID=0b334931-f5b3-4f86-a319-978db2096734

AUTOMATIC_FOLLOWUP_TRIGGER_STATUS=PARTIAL_REAL_BOUNDED — backend queue and worker are deployed, but the currently served GoClear frontend bundle predates the adapter invocation, so the deployed browser did not yet prove the automatic call.

FOLLOWUP_MESSAGE_ID=goclear-followup-2d18311d-439d-4b71-8192-e3b65f45eba0

FOLLOWUP_PROVIDER_MESSAGE_ID=01a0c5c6-704f-76be-85c9-2d514c1c034f

FOLLOWUP_ACCEPTED_STATUS=PASS_REAL — Resend accepted the controlled canary and returned the provider message ID.

FOLLOWUP_DELIVERY_STATUS=PASS_REAL — the same canary reached `delivered@resend.dev`; canonical `marketing_email_messages.delivery_status=DELIVERED` and the follow-up job status is `delivered`.

FOLLOWUP_DELIVERED_AT=2026-09-21T21:01:52.261Z

## === WEBHOOKS ===

WEBHOOK_ENDPOINT=https://iqjwgpnujbeoyaeuwehj.supabase.co/functions/v1/goclear-resend-webhook

WEBHOOK_SIGNATURE_VALIDATION=PASS_REAL — raw body verification uses Resend/Svix `svix-id`, `svix-timestamp`, and `svix-signature` headers with the server-only Resend signing secret; stale timestamps are rejected.

UNSIGNED_WEBHOOK_REJECTED=PASS_REAL — HTTP 401, no event mutation.

INVALID_SIGNATURE_REJECTED=PASS_REAL — HTTP 401, no event mutation.

VALID_SIGNATURE_ACCEPTED=PASS_REAL — real Resend `email.sent` and `email.delivered` callbacks persisted with `signature_verified=true`.

SIGNED_EMAIL_WEBHOOK_STATUS=PASS_REAL

EMAIL_EVENT_NORMALIZATION_STATUS=PASS_REAL_BOUNDED — sent, delivered, bounced, clicked, complained, and suppressed/unsubscribe-compatible provider states map to the existing canonical email/distribution records; signed delivered state was proven end to end.

## === SUPPRESSION ===

MARKETING_SUPPRESSION_REGRESSION=PASS_REAL — the synthetic suppression state blocked the follow-up worker with an explicit `followup_blocked_suppressed` result. The suppression row was removed afterward so the controlled delivery canary could run; no real recipient was affected.

## === BETA PROJECTION ===

BETA_JOURNEY_PROJECTION_STORE=public.goclear_beta_journey_projection, refreshed by `goclear_refresh_beta_journey_projection(text)` from the existing lead, upload, readiness, Clyde, report, review, email, and feedback records.

BETA_JOURNEY_PROJECTION_STATUS=PASS_REAL — the controlled canary projection recorded `feedback_submitted`, report `ready`, review `pending_admin_review`, follow-up `delivered`, provider message ID, blocking issue, and Ray-action state.

## === NOVA ===

NOVA_BETA_VISIBILITY_STATUS=PARTIAL_REAL_BOUNDED — the canonical projection and Nova monitor component are implemented in the source build, but the public bundle still serves the prior Nova surface. Browser certification against the deployed Nova projection panel is therefore held.

## === ADMIN ===

ADMIN_BETA_ROUTE_OR_COMPONENT=existing `/admin` command center with the read-only `GoclearBetaProjectionPanel` mounted on the dashboard; the same projection is mounted in the Nova AI Command surface.

ADMIN_BETA_BROWSER_STATUS=HELD — deployed frontend bundle has not yet mounted the new projection panel.

ADMIN_BETA_VISIBILITY_STATUS=PARTIAL_REAL_BOUNDED — source implementation is present and builds locally; deployed Admin readback is not certified.

## === RELEASE CANARY ===

BETA_RELEASE_CANARY_ID=0b334931-f5b3-4f86-a319-978db2096734

AUTOMATIC_FOLLOWUP_TRIGGER_STATUS=PARTIAL_REAL_BOUNDED

SIGNED_EMAIL_WEBHOOK_STATUS=PASS_REAL

FOLLOWUP_DELIVERY_STATUS=PASS_REAL

BETA_JOURNEY_PROJECTION_STATUS=PASS_REAL

NOVA_BETA_VISIBILITY_STATUS=PARTIAL_REAL_BOUNDED

ADMIN_BETA_VISIBILITY_STATUS=PARTIAL_REAL_BOUNDED

BETA_RELEASE_CANARY_STATUS=PARTIAL_REAL_BOUNDED — canonical review event, queued job, Resend acceptance, signed sent/delivered events, canonical delivery update, and projection update passed. Deployed automatic invocation plus Nova/Admin browser readback remain pending.

## === FINAL ===

CORE_CLIENT_JOURNEY_STATUS=PASS_REAL_BOUNDED

AUTOMATIC_FOLLOWUP_TRIGGER_STATUS=PARTIAL_REAL_BOUNDED

SIGNED_EMAIL_WEBHOOK_STATUS=PASS_REAL

FOLLOWUP_DELIVERY_STATUS=PASS_REAL

NOVA_BETA_VISIBILITY_STATUS=PARTIAL_REAL_BOUNDED

ADMIN_BETA_VISIBILITY_STATUS=PARTIAL_REAL_BOUNDED

GOCLEAR_FRIENDS_BETA_CERTIFICATION=PARTIAL_REAL

GOCLEAR_READY_FOR_FRIENDS_BETA=NO

WAVE_1_PREP_STATUS=NOT_PREPARED_GATED — no invitations or Wave 1 tester slots were sent or activated.

TRUE_EXTERNAL_BLOCKERS=The approved Netlify deployment control path is unavailable in the current runtime, so the new frontend bundle cannot be published and the deployed automatic follow-up invocation/Nova/Admin projection panels cannot be certified. Social publishing remains held and is non-blocking.

RAY_ACTION_REQUIRED=Restore or authorize the existing approved Netlify deployment path for this repository. No customer, Resend, social, or paid-media credential request is needed; the Resend webhook is already registered and secret-configured.

NEXT_MACHINE_ACTION=Publish the current built bundle through the approved Netlify path, rerun one browser review request without manual worker invocation, verify the follow-up job/provider delivery, then browser-read the Nova and Admin projection panels and update this report.

## Provider evidence note

Resend webhook verification follows the provider’s raw-payload Svix signing contract and uses the provider-returned webhook signing secret. Resend documents that webhook verification must use the raw request body and the `svix-id`, `svix-timestamp`, and `svix-signature` headers: [Managing Webhooks via API](https://resend.com/changelog/managing-webhooks-via-api).
