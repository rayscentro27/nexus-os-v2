# Telegram Result Rendering Certification

WP5 execution responses now consume the verified `output_artifact` payload
from the loop receipt and render answer-first summaries. Receipt identifiers
and paths remain internal evidence and are not the primary Telegram answer.

Certified bounded renderers cover system operations, private research, repo
intelligence, and review-queue state. Missing structured output returns
`RESULT_INSUFFICIENT_FOR_SUMMARY` rather than inventing facts. TruthKernel,
authority, verification, and fail-closed behavior are unchanged.
