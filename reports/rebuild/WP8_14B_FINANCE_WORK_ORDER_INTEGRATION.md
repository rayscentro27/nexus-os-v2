# WP8.14B Work-order integration

`finance_preflight` and `finance_postrun` are the canonical boundary. Preflight captures work order, department, initiative/campaign/strategy, envelope, estimates, authority, resource state, and returns `ALLOW`, `BLOCK_BUDGET`, `BLOCK_AUTHORITY`, or `UNKNOWN_REQUIRES_REVIEW`. Postrun records actual cash, credits, quota, compute, storage, replacement estimate, status, attempt/retry identity, and estimate-vs-actual variance. Failed work is still recorded.
