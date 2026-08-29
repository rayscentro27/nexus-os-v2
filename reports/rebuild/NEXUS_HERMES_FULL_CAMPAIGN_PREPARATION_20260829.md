# Hermes Full Installation and Mac Integration Campaign Preparation

`HERMES_FULL_CAMPAIGN_PREPARED=YES`

Campaign gate: `HG-WP2-HERMES-FULL-INSTALL-INTEGRATION-20260829-01`

Status: `PENDING`

This is one bounded TruthKernel authorization covering Oracle Hermes 0.20.6
installation, lifecycle repair, runtime/config/session/memory certification,
supported feature inventory and guarded activation, and private Mac-to-Oracle
Nexus integration. Approval must arrive through the existing authorized human-
gate route; this repository record is not approval.

Narrow Hermes installation/deployment gates are operationally superseded by
this campaign. Pending narrow gates were held through TruthKernel semantics.
Previously approved narrow gates remain immutable historical records and were
annotated with supersession events; none is to be reused.

## Included authority

- Existing Oracle Linux 9.7 aarch64 VM and rootless Podman 5.8.2.
- Persistent rootless user-manager lifecycle repair for `opc`, including
  `loginctl enable-linger opc` if required by observed state.
- Pinned official Hermes Agent 0.20.6 ARM64 image/tag/commit and isolated
  `/opt/data` state; forensic partial state is preserved.
- Protected local API-key handling without printing or committing secrets.
- Existing Oracle Ollama `gemma3:4b` provider, without Ollama changes.
- Hermes runtime certification, logout/container restart durability, supported
  feature inventory, and guarded feature activation.
- Private Mac loopback bridge over controlled SSH forwarding with correlated,
  advisory Nexus requests and TruthKernel remaining authoritative.
- Evidence-based corrective retries, user-level supervision, tests, receipts,
  sanitized reports, commit, and push.

## Explicit exclusions

No public Hermes endpoint, public DNS, firewall/OCI change, cloud provisioning
or resize, paid service, unknown/new credential, credential rotation, payment,
live trading, client-production mutation, privileged container, unrestricted
root authority, broad host filesystem/socket/SSH-key mount, TruthKernel or Nexus
source mount, uncontrolled external communication, or real Telegram Hermes E2E.
Active Operator remains paused. External gateways without already authorized
credentials are classified `BLOCKED_EXTERNAL_DEPENDENCY` rather than bypassed.
