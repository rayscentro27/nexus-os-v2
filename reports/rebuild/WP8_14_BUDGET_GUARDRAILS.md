# WP8.14 Budget Guardrails

Supported envelope keys include `MAX_CASH_COST_USD`, `MAX_FREE_CREDIT_USAGE`, `MAX_MODEL_TOKENS`, `MAX_GPU_MINUTES`, `MAX_MAC_HEAVY_MINUTES`, `MAX_ORACLE_COMPUTE_MINUTES`, and `MAX_STORAGE_BYTES`. At or above an envelope the optional task pauses, state and receipt are preserved, and Finance/owner review is requested. Unknown balances remain unknown and cannot be treated as remaining capacity.
