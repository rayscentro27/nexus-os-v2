# Telegram Result Rendering Certification

WP5 execution responses now consume the verified `output_artifact` payload
from the loop receipt and render answer-first summaries. Receipt identifiers
and paths remain internal evidence and are not the primary Telegram answer.

Certified bounded renderers cover system operations, private research, repo
intelligence, and review-queue state. Missing structured output returns
`RESULT_INSUFFICIENT_FOR_SUMMARY` rather than inventing facts. TruthKernel,
authority, verification, and fail-closed behavior are unchanged.

The repository renderer now reports branch, HEAD/message, upstream relationship,
ahead/behind counts, worktree counts, grouped changed paths, expected campaign
versus pre-existing changes, verification fields, and actionable next steps.
The research renderer consumes executive summary, findings, changes, importance,
uncertainties, and sources-used fields. Ray Review retains its operator-facing
item format and adds recommended decision and priority.

Focused local certification: 9 tests passed. The latest live Telegram poll was
healthy but contained no updates, so live communication-quality retests remain
not proven; no live result is claimed from bounded local equivalents.
