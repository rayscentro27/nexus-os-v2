# Needle / Jev Technology Assessment

Date: 2026-09-27

## Evidence boundary

The original aggregate GitHub search did not identify a single unambiguous
Needle/Jev pair. Bounded source recovery therefore separated the candidates;
it did not treat similarly named projects as one product.

## Needle

Matched identity: `needle-ai/needle-mcp`, an MCP server for Needle document
management and retrieval/RAG.

Official sources:

- https://github.com/needle-ai/needle-mcp
- https://needle.app/docs/mcp/introduction

The repository page identifies an MIT license, and the README documents remote
MCP plus local `uv` and Docker paths. Needle’s official docs describe a remote
MCP endpoint, OAuth/API authentication, and document/lead/campaign tools. The
current evidence does not establish Intel-Mac performance, exact local CPU/RAM
needs, version pinning, or a Nexus benchmark result.

Assessment: potentially useful for MCP document retrieval and long-term memory,
but overlap, data boundaries, authentication, and value versus existing Nexus
Research remain unproven. Do not install it on the Mac. Oracle or the remote
worker would be the safer future assessment host if the candidate is confirmed
as the intended product.

## Jev

Jev remains ambiguous across at least two materially different candidates:

1. Hosted Jev AI / TypeSafe-style typed decision model, represented by
   https://github.com/jev-ai and its linked product documentation.
2. Community `okooo5km/jev` CLI at
   https://github.com/okooo5km/jev/blob/main/README.en.md, whose README
   documents macOS/Linux installation, v0.3.2, Apache-2.0, typed decision
   specs, and a hosted/API or OpenRouter path.

The hosted model’s license, local weights, and self-hosting terms were not
established by the original Nexus evidence. The community CLI is not proof
that it is the product Ray intended, and it must not be silently substituted.

Assessment: typed decision routing could improve queue triage, guardrails, or
model routing, but the exact target, terms, resource footprint, and comparison
against current Nexus capability are unresolved. No installation or API spend
was attempted.

## Source recovery ledger

| Source class | Source | Result |
|---|---|---|
| Aggregate search | GitHub Needle/Jev search | Ambiguous; insufficient as final identity evidence. |
| Official repository | `needle-ai/needle-mcp` | Strong Needle identity; MIT; MCP/RAG purpose. |
| Official documentation | `needle.app/docs/mcp/introduction` | Remote MCP/authentication and capability evidence. |
| Community repository | `okooo5km/jev` README | Apache-2.0 community CLI, v0.3.2 installation and typed decision behavior. |
| Product organization | `jev-ai` GitHub | Hosted typed-decision product identity. |
| Secondary identity guide | `devwithjev.com/guides/is-jev-open-source` | Reports hosted Jev model is proprietary; treated as secondary, not universal authority. |

## Compatibility and test decision

Current evidence confidence: `PARTIAL` for Needle; `LOW/PARTIAL` for Jev due
identity ambiguity.

Current Systems disposition: `NEEDS_MORE_EVIDENCE`.

Future test host: `ORACLE` first, or the certified remote worker control plane.
The Intel 8 GiB Mac is not the default test host because it is the production
control plane. A future isolated test needs a pinned candidate, license/terms,
runtime and dependencies, resource limits, success/failure metrics, rollback,
cleanup, and zero production touch.

Required next Research question: “Which exact Needle and Jev products did Ray
intend, and what official license/terms, pinned version, runtime, dependencies,
resource requirements, and benchmark evidence support an isolated Oracle test?”
