# Ray Review + Telegram Lane Integration

**Generated**: 2026-07-05
**Phase**: E

## Approval Packet Format

Every approval packet includes:

| Field | Description |
|-------|-------------|
| item_id | Unique identifier (EMAIL-001, SOCIAL-001, STRIPE-001) |
| lane | customer_email, social_publishing, stripe_test_checkout |
| title | Human-readable title |
| safe_summary | Telegram-safe preview (no sensitive data) |
| risk_level | low, medium, high |
| required_approval | Approval type needed |
| required_runner | Runner that executes after approval |
| required_env | Environment variables needed |
| required_receipt | Receipt path |
| current_status | Current workflow state |
| next_action | Exact next step |
| receipt_path | Path to receipt file |
| dashboard_link | Admin dashboard reference |
| workflow | Step-by-step workflow with status |

## Telegram Commands

| Command | Action | Safe |
|---------|--------|------|
| `/review` | Show pending approval packets | YES |
| `/approve ID` | Approve an item | YES |
| `/reject ID reason` | Reject with reason | YES |
| `/revise ID feedback` | Request revision | YES |

## Sensitive Data Rule

Telegram shows only safe summaries. Full content is in approval packets on disk.
No client email addresses, no full post content, no payment details in Telegram.

## Lane Integration Status

| Lane | Packet Format | Telegram Support | Status |
|------|--------------|-----------------|--------|
| Customer Email | READY | READY | APPROVAL_GATED_READY |
| Social Publishing | READY | READY | APPROVAL_GATED_READY |
| Stripe Test Checkout | READY | READY | APPROVAL_GATED_READY |
