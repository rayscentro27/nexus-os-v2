# Future Read-Only Research Vault Adapter

Not implemented or connected.

The future adapter may query a narrow allowlist of curated, non-client research views through a dedicated read-only identity. It must have no broad table access, RPC/write/storage access, service-role credential, client/tenant records, operational queues, secrets, or production mutation.

Return evidence packets only: source ID, title, excerpt/summary, provenance, timestamps, quality, sensitivity, allowed lanes, and view/version. Alpha still applies objective → brain → model/research → memory/framework → output order; the vault never becomes source authority.

Every query needs an allowlisted view, bounded result/size/time, audit receipt, redaction, and denial-by-default. Nexus Hermes later reads only Ray-approved Alpha outputs promoted through the bridge—not raw Alpha memory or vault results.

Activation prerequisites: data classification, view definitions, threat model, RLS/read-only verification, test tenant with no client data, prompt-injection policy, retention, revocation, audit tests, and separate Ray approval.
