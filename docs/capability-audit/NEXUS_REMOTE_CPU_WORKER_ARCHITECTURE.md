# Nexus Remote CPU Worker Foundation

Phase I adds a provider-neutral worker contract and a fixed-command Linux container definition. The control path is `Nexus -> governed remote job -> provider adapter -> allowlisted worker capability -> structured result -> Nexus validation -> receipt -> Mission Control`.

The worker is compute only. It cannot create work orders or approvals, mutate Mission Control, invoke Active Operator or Recovery Check, publish, message, move money, trade, or execute arbitrary commands. It exposes authenticated `/v1/jobs` and read-only `/health`; it is not a scheduler.

The selected deployment target for the live pilot is **not yet selected**. No usable existing Linux host or running local container daemon was found, and no cloud infrastructure was provisioned. The container is ready for a later Linux provider once authenticated, bounded execution and teardown are available.
