# Order and Fulfillment Lifecycle

An order starts as `draft`, becomes `checkout_created` and `payment_pending`, and reaches `paid` only after a verified Stripe webhook. Failed, expired, cancelled, refunded, and disputed states remain explicit.

After verified payment, exactly one `service_fulfillments` row is created with `onboarding_required`. The controlled path is:

`not_started → onboarding_required → intake_in_progress → awaiting_documents → analysis_in_progress → admin_review → ray_review (when required) → approved_for_delivery → delivered → completed`

Invalid transitions are rejected by the application transition model and controlled admin actions. A blocked or cancelled path is never silently treated as complete.

The client can read only its own order and fulfillment through tenant membership and auth-user linkage. The client has no write policy for payment state, amount, provider IDs, assignment, approval, or delivery. Active admins can review and operate authorized orders. Payment events are admin-visible and server-written.

Order numbers are unique. Provider event IDs, checkout session IDs, and payment intent IDs are unique. Provider and ownership fields are immutable after persistence. Reset utilities delete only Persona D revenue rows and never delete Auth accounts, client profiles, offers, or other personas.
