# Nexus Approval-Gated Lane Guard

**Generated**: 2026-07-05
**Phase**: G

## Lane Guard Status

| Lane | approval_gated | autonomous_execution | required_runner | required_env | current_status |
|------|---------------|---------------------|-----------------|--------------|----------------|
| customer_email | true | false | resend_api_runner | RESEND_API_KEY | CUSTOMER_EMAIL_APPROVAL_GATED_READY |
| social_publishing | true | false | {platform}_publish_runner | {PLATFORM}_ACCESS_TOKEN | SOCIAL_PUBLISHING_APPROVAL_GATED_READY |
| stripe_test_checkout | true | false | stripe_test_checkout_runner | STRIPE_SECRET_KEY | STRIPE_TEST_CHECKOUT_READY |

## Guard Rules

- All external actions require Ray approval
- All actions check for required env vars before execution
- All actions write receipts
- No autonomous execution without approval
- Telegram can approve/reject/revise but cannot bypass guard
- No sensitive client data in Telegram summaries
