# Hermes integration

The dedicated Nova profile now defines the profile-local `nexus_mcp` stdio server and enables the `mcp-nexus_mcp` toolset. The Nova runner explicitly performs Hermes MCP discovery at bounded synchronous entrypoint startup, because Hermes removed discovery as a module-import side effect.

The legacy `nexus_read_shadow` adapter remains compatibility-only behind `NOVA_ENABLE_LEGACY_SHADOW_NEXUS=true`; it is not registered in normal Nova execution. Web and Alpha adapters remain unchanged.

The live Hermes shadow probe discovered all six MCP tools and executed the six read tools for the Nexus attention question. The resulting state contained concrete blockers, a queued work order, health, approvals, and business-state details.

