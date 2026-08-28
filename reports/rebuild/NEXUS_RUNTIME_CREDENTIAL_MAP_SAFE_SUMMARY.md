# WP0-F — Repository-Safe Runtime Summary

This public artifact intentionally excludes host identity, personal paths,
remote addresses, SSH key locations, session stores, and detailed credential
inventories. The full value-free operational map is local-only under the
canonical Nexus configuration area.

## Verified safe facts

- Host class: Intel Mac mini, 8 GB class hardware.
- Operating system: macOS 12.7.6 / Darwin 21.6.0.
- Nexus uses a repository-local Python environment and deterministic Python
  entrypoints.
- A canonical runtime-environment wrapper exists and is used by selected
  launchd workers.
- Hermes has a separate local gateway/auth configuration boundary.
- Provider credential sources include canonical runtime configuration, local
  legacy configuration, Hermes configuration, and possible macOS Keychain
  integration.
- Canonical runtime environment source: **PRESENT**.
- Local legacy/recovered environment sources: **PRESENT; duplicate-source risk**.
- Hermes auth/configuration source: **PRESENT; values not inspected**.
- macOS Keychain source: **UNKNOWN; values not inspected**.
- Oracle/Ollama capability has a supervised private tunnel declaration; tunnel
  health is **NOT_VERIFIED** by this map.
- Launchd declarations were observed as loaded for multiple Nexus/Hermes
  labels. Loaded is not equivalent to running, responding, executing, or
  healthy.
- Active Operator remains paused by safety policy.

## Verified architecture conclusions

`launchd → runtime environment wrapper → bounded Python entrypoint → runtime
report/receipt` is the intended chain. Multiple legacy callers can read local
environment files independently, so source precedence and scope remain a
Sprint 1 operational-truth concern.

No secret values, tokens, passwords, JWTs, cookies, private-key material,
hostnames, usernames, IP addresses, exact credential paths, or session-store
paths are included here.

## Local evidence

See the local-only map at:

`~/.config/nexus/nexus_rebuild_runtime_credential_map.local.json`
