# WP8.11B Remote Creative Worker

REMOTE_CREATIVE_WORKER_CONTRACT=IMPLEMENTED
REMOTE_CREATIVE_WORKER_AUTHORITY=COMPUTE_ONLY
REMOTE_CREATIVE_WORKER_SECURITY=PASS
REMOTE_RENDER_RECOVERY=PASS
CREATIVE_COMPUTE_FALLBACK_POLICY=PASS
CREATIVE_PAID_SPEND_AUTHORITY=NONE

The contract carries render job, asset, input refs, workflow/model, dimensions, duration, budget, authority, and timeout; returns status, artifact, logs, runtime, cost, resource, and receipt. Worker credentials are intended to be job-scoped and asset-scoped. Current execution remains blocked until a legitimately configured worker exists.
