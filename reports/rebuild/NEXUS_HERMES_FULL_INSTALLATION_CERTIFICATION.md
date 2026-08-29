# Hermes Full Installation Certification — 2026-08-29

`HERMES_FULL_CAMPAIGN_COMPLETE=YES_WITH_LIMITS`

Campaign gate: `HG-WP2-HERMES-FULL-INSTALL-INTEGRATION-20260829-01`.

Oracle Hermes Agent `0.20.6`, tag `v2026.8.27`, commit `5fc308a7`, and the
approved ARM64 digest are running under rootless Podman `5.8.2`. The runtime
uses a Quadlet user service, an isolated certification state directory, host
networking only for the already-approved loopback Ollama dependency, and an
API listener restricted to `127.0.0.1:8642`. No public endpoint, firewall
change, OCI change, privileged mode, host filesystem, SSH-key, socket,
TruthKernel, or Nexus-source mount is present.

Certified:

- API authentication rejects requests without the protected local key and
  accepts requests with the valid key.
- Hermes reaches Oracle Ollama `gemma3:4b` and returns a successful reasoning
  response.
- Session creation, session read/resume metadata, and persisted messages pass.
- Built-in memory storage wrote a synthetic marker through the tagged Hermes
  memory implementation and the marker survived container restart.
- Default profile is running; an isolated secondary profile was created.
- Bundled skills were synchronized and the authenticated skills endpoint is
  available; API toolsets remain empty by design for the minimum provider-
  compatible profile.
- `loginctl enable-linger opc` and Quadlet user supervision prevent the prior
  SSH-session cleanup exit-137 failure. A new SSH session found the service
  running after logout.
- Container restart restored API, provider, session, and memory state.
- Mac loopback `127.0.0.1:18642` forwards privately over SSH to Oracle
  `127.0.0.1:8642`; the Nexus adapter completed a synthetic correlated
  advisory request.

Not claimed: VM reboot recovery, continuous-runtime proof, real Telegram E2E,
external gateway credentials, paid providers, or consequential Hermes
authority. Browser, MCP, shell, delegation, voice, routines, and other
powerful capabilities remain disabled or Nexus-wrapped/blocked as recorded in
the feature inventory.
