# Hermes UI Action Rendering Result

The full Hermes Workroom and inline drawer now retain structured `uiActions` from the brain response and render allowlisted navigation buttons.

- Report actions open the Report Center.
- Approval actions open Ray Review; they do not approve or reject.
- Access-map actions open Hermes Workroom.
- Unknown, external, or mutating actions are rejected by the allowlist.

Current limitation: parent screens open, but selected report/approval IDs are not yet transferred into screen selection state. The metadata retains `reportPath` or `approvalId` for a later deep-link implementation.

