# Nexus / Oracle Hermes Architecture

## Ownership

The Mac mini is the Nexus control plane: TruthKernel, human authority and
gates, deterministic Python, business engines, work orders, receipts, and the
Telegram approval route. The Oracle VM is an intelligence node: Hermes Agent
0.20.6, reasoning, conversation, sessions/memory, research, approved skills
and tools, provider routing, and bounded retry/fallback.

Hermes is advisory. It cannot approve gates, mutate TruthKernel, verify side
effects, make payments, trade, alter client production data, deploy production
changes, send unrestricted messages, rotate credentials, install software, or
start Nexus services. Python remains the deterministic executor and trading
hot path.

## Private bridge

Hermes uses the official OpenAI-compatible API (`/health` and
`/v1/chat/completions`) on loopback. The initial transport is a controlled SSH
local forward from the Mac to the Oracle loopback listener. Proposed Mac
endpoint: `http://127.0.0.1:18642`; Oracle Hermes bind: `127.0.0.1:8642`.
No Hermes endpoint, DNS record, public tunnel, OCI ingress, or public port is
created.

Bridge requests carry a correlation ID, bounded request type, purpose,
read-only safe context, capability allowlist, timeout, and data classification.
PII is denied by default. Responses carry the same ID, status, advisory result,
model/provider metadata, tool usage, warnings, error, and timestamps. A bridge
failure is explicitly unavailable; it never becomes a successful Nexus run.

## Runtime state and safety

Oracle Hermes state is isolated from the Nexus source tree in a protected
Oracle-local runtime directory. Secrets are loaded through an existing secure
mechanism and are never committed. Ollama and SearXNG remain independent
services and are not reconfigured.

Initial feature disposition: Bot Mode, scoped sessions/memory, allowlisted
skills, wrapped MCP/browser/tools, wrapped provider routing, and bounded
retry/fallback. Routines, delegation/subagents, voice, and Active Operator are
disabled. `ACTIVE_OPERATOR_PAUSED=YES`; live and automatic trading are
disabled; paper-only mode remains in force; payments, external email, social
publishing, client production mutation, and autonomous Codex worker
authorization remain disabled.
