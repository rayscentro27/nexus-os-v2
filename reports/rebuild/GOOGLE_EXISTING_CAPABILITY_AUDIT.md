# Google Existing Capability Audit

The existing adapter is `scripts/nexus_agent_platform/google_workspace.py`.
It provides refresh-only Google credentials and read probes for Gmail and
Calendar. No existing granular Google MCP server was present.

| Capability | Existing implementation | This phase |
|---|---|---|
| Gmail read | Google API client certification | wrapped by read-only MCP |
| Gmail write | no exposed adapter | not exposed |
| Calendar read | Google API client certification | wrapped by read-only MCP |
| Calendar write | governed capability metadata only; no callable adapter | not exposed |
| Drive | existing certification probe | explicitly out of scope |

The new server reuses the credential path and does not invoke the old
agent-platform brain.
