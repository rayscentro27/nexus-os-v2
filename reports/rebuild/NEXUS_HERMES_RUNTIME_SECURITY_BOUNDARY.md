# Hermes Runtime Security Boundary — 2026-08-29

Hermes runs rootless under Podman `5.8.2` with the pinned official ARM64
image. Host networking is accepted only because Oracle Ollama listens on host
loopback; the Hermes API binds to `127.0.0.1:8642` and has no Podman port
publish. The Mac path is a loopback-only SSH forward.

Proven controls:

- no public Hermes endpoint, public dashboard, public Podman socket, firewall,
  or OCI ingress change;
- no privileged mode, added capabilities, runtime socket, SSH-key mount,
  TruthKernel mount, Nexus source mount, or broad host filesystem mount;
- isolated `/opt/data` state and protected API key outside Git;
- API platform toolsets empty for the minimum provider-compatible profile;
  browser, MCP, terminal, code execution, voice, routines, delegation, and
  autonomous external actions are disabled;
- Nexus remains authority; Hermes output is advisory and the bridge rejects
  PII by default;
- Active Operator paused; payments, live trading, and client-production
  mutations remain disabled.

Host networking is a broader boundary than bridge networking, but its approved
use is bounded to the existing private Oracle host and loopback provider. No
additional host-local service was granted through mounts, sockets, or tools.
