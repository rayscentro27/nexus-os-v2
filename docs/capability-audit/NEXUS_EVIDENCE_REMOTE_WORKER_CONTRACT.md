# Remote-Worker-Ready Evidence Contract

No remote infrastructure was provisioned in Phase H. The local worker already accepts a serializable envelope containing job ID, capability, adapter, source, policy, limits, tenant context, and request time. Results contain status, artifact/receipt references, hashes, provenance, and metrics.

Future remote execution must preserve Nexus as authority: `Nexus -> governed job -> worker -> structured result -> Nexus validation -> receipt -> Mission Control`. A worker may acquire/convert evidence only within the request policy. It may not create approvals, work orders, external actions, recommendations, or canonical state.

Next-phase prerequisites are a provider-neutral worker interface, authenticated job transport, tenant isolation, bounded queue/retry semantics, secret-free payload design, receipt correlation, and failure isolation from the core runtime.
