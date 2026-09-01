# Nexus MCP System-Health Semantics

The health read uses the live shared resolver and distinguishes:

- service/process registry state;
- Nexus runtime state;
- worker availability/capacity;
- configured, disabled, stale, blocked, and failed components.

`active_services=0` in a process projection does not mean Nexus is down. The
returned state must be qualified when telemetry is partial. The live report
also records `nexus_running=YES` and available worker capacity.

The MCP result therefore reports `currentness=CURRENT` with `status=partial`
when the live query completed but some telemetry sources are incomplete.

FALSE_LIVE_HEALTH_CLAIM=NO
