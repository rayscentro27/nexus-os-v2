# Nexus Remote CPU Worker Foundation

Phase I adds a provider-neutral worker contract and a fixed-command Linux container definition. The control path is `Nexus -> governed remote job -> provider adapter -> allowlisted worker capability -> structured result -> Nexus validation -> receipt -> Mission Control`.

The worker is compute only. It cannot create work orders or approvals, mutate Mission Control, invoke Active Operator or Recovery Check, publish, message, move money, trade, or execute arbitrary commands. It exposes authenticated `/v1/jobs` and read-only `/health`; it is not a scheduler.

Phase I-C selects **Modal** as the bounded provider adapter for the live CPU
pilot. Modal-native authenticated function invocation is used by the Nexus
provider; the worker additionally verifies the existing Nexus HMAC. The
deployment is CPU-only, min-containers 0, max-containers 1, with a bounded
timeout and no retry loop. OCI remains deferred.

Modal-specific IDs and transport details stay behind the provider adapter.
`nexus.remote-job.v1`, `nexus.remote-result.v1`, tenant semantics, evidence
hashes, receipts, and Mission Control remain provider-neutral. Modal is
compute only: Nexus retains control, governance, authority, and canonical
state.
