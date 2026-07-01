# Hermes Memory Boundary Bug

The failure was not a Level 3 entity resolution leak. The existence of memory made every otherwise-unmatched message eligible for the Level 4 default. Level 4 then returned the readiness recommendation as its universal fallback. Casual and trading messages therefore produced the same stale business answer even though neither contained a valid memory reference.

The patch adds semantic domain classification, a non-destructive topic boundary, activation pre-checks, guarded reasoning context, and domain-specific Level 4 construction. Stored memory is preserved but excluded from a response unless eligibility passes.

The number-reference matcher was also generalized so prefixed continuations such as “So number 3…” correctly report Level 3.
