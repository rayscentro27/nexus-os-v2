# Nexus MCP server foundation

`services/nexus_mcp/server.py` is a local stdio FastMCP server using MCP 1.28.1. It exposes exactly six read-only tools and writes one redacted receipt per call under the runtime receipt directory.

The server has no mutation tools, arbitrary command execution, SQL access, credentials, or provider logic. Startup, initialize, discovery, schema, all-tool invocation, and receipt creation were exercised successfully.

