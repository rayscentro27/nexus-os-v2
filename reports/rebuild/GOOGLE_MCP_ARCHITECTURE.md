# Google MCP Architecture

Architecture: separate local-stdio `services/google_mcp/server.py`, connected
to the dedicated Nova Hermes profile. Nexus MCP remains the company-state
interface; Google MCP is the external Google capability interface.

The server exposes six granular read tools:

- `gmail_search`, `gmail_read_message`, `gmail_read_thread`
- `calendar_search_events`, `calendar_read_event`, `calendar_get_availability`

Hermes discovers the server natively. The server uses deterministic API calls,
bounded results, explicit query windows, and read-only receipts. It has no
send, draft, event mutation, invitation response, contact, Drive, or Docs
surface.

`MCP_DOES_NOT_GRANT_AUTHORITY=YES`
