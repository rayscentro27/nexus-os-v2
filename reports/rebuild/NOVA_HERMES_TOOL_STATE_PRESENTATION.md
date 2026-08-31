# Tool-state presentation contract

`_tool_execution_state()` now passes current-turn facts to final presentation: search, retrieval, Nexus, and Alpha execution booleans; per-tool counts/statuses; retrieved-page count; currentness values; and retrieval status.

Precedence is actual tool result, current-turn receipt, current-turn plan, then prior context. If retrieval completed, Nova cannot say URLs still need retrieval. If retrieval did not execute, Nova cannot imply page review. Weak evidence is described as weak rather than promoted to verification.

The general advice contract is reasoning-first when no resource is explicitly required. Explicit Nexus, web/current, and Alpha requests remain executable. A named volatile subject such as Tesla with “right now” still requires public web evidence.

Regression evidence: general preflight used zero tools; Tesla used public search and retrieval; the linked multi-resource preflight executed Nexus and web retrieval and its final text reflected the completed state without claiming retrieval was pending.
