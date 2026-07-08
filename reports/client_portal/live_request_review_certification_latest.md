# Request Review Workflow Certification — Client Portal

**Date:** 2026-07-08
**Starting Commit:** 71b9dd4

---

## Request Review Page Analysis

### Page Component: `RequestReviewPage` (ClientPortalPages.jsx)

#### Metrics Displayed
- Review Readiness: funding.readinessScore (68)
- Open Tasks: count of tasks with status !== 'complete'
- Review Status: "Not submitted"

#### Warning Box
- Title: "Complete open tasks first"
- Body: "Request review only after completing all high-priority tasks. Incomplete submissions may delay processing."

#### Open Tasks List
- Shows tasks with `_route` navigation to relevant pages
- Each task item is clickable and navigates to the correct page

#### What Happens After Review
- "GoClear reviews your readiness profile"
- "You receive a status update in Messages"
- "Next steps are recommended based on review"
- "No application is submitted without your approval"

#### Submit Button
- **Status:** DISABLED
- Text: "Request Review (complete tasks first)"
- Style: gray background, gray text, cursor: not-allowed
- Reason: tasks are not complete (all 4 tasks have status !== 'complete')

---

## Expected Behavior vs Actual

| Check | Expected | Actual | Result |
|---|---|---|---|
| Client can open Request Review page | Page loads | Page renders with metrics + tasks | PASS |
| Page explains review is not a guarantee | Disclaimer present | Warning box + "no application without approval" | PASS |
| Client can submit or see clear state | Button visible | Disabled button with reason text | PASS |
| Submit writes to review queue | Not implemented | Button disabled, no backend write | NOT IMPLEMENTED |
| Admin can see request | Not implemented | No admin review queue integration | NOT IMPLEMENTED |
| Hermes/admin can review | Not implemented | No review workflow | NOT IMPLEMENTED |

---

## Current State

The Request Review page is **functional as a display page** but **not as a submission workflow**:

1. ✅ Page loads and shows readiness data
2. ✅ Explains review is not a guarantee
3. ✅ Shows open tasks that need completion
4. ✅ Button is disabled with clear reason
5. ❌ No actual review submission mechanism
6. ❌ No admin review queue integration
7. ❌ No Hermes/admin review workflow

---

## Summary

| Check | Result |
|---|---|
| Client can open Request Review page | PASS |
| Page explains review is not a guarantee | PASS |
| Client can submit or see clear setup-in-progress state | PASS (disabled with reason) |
| Submit writes to client_tasks or review queue | NOT IMPLEMENTED |
| Admin can see the request | NOT IMPLEMENTED |
| Hermes/admin can review before external action | NOT IMPLEMENTED |

**STATUS: Placeholder only — not ready for real tester submissions.**
The page is safe and informative. The disabled button clearly communicates "complete tasks first."
