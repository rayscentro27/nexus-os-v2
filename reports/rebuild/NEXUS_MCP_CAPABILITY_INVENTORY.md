# Nexus MCP capability inventory

MCP is an interface only. It does not grant authority.

| Capability | Current adapter | Authority owner | Truth owner | Read/write | MCP suitable | Complexity |
|---|---|---|---|---|---|---|
| Clients, reviews, business state | governed operational-read capability broker | Nexus policy | Nexus ledgers/reports | read-only | yes | medium |
| Opportunities and revenue state | operational reads and revenue artifacts | Nexus policy | Nexus artifacts/ledgers | read-only | yes | medium |
| Work orders and approvals | capability broker and governed queue | Nexus authority/TruthKernel | Nexus receipts | read/write, governed | yes, gated | high |
| System health and runtime state | operational-read capability registry | Nexus policy | runtime ledgers | read-only | yes | low |
| Research requests | `submit_alpha_request` / Alpha adapter | Nexus request policy | Alpha receipts/artifacts | request/write, governed | yes, gated | medium |
| Campaigns and publishing | approval/work-order interfaces | Nexus authority | Nexus receipts | mutation, governed | yes, gated | high |

The installed Hermes runtime supports MCP 1.26.0 with stdio, Streamable HTTP,
SSE, tool discovery, schemas, sessions, headers, and OAuth 2.1 PKCE. A future
MCP phase can expose read-only capabilities first, followed by explicitly
governed request interfaces.
