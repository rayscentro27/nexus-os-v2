# Nexus Tool Scope and Salience Audit

## Current tool surface

The six Nexus tools are read-only MCP capabilities: reviews, work items,
blockers, opportunities, business state, and system health. They are available
through the dedicated Hermes-native profile alongside Google, Web, and Alpha.
The registration order is the profile/toolset order, with Nexus before Google,
Web, and Alpha; this is a possible salience factor but not a routing rule.

The operational descriptions are narrow for reviews, work items, blockers, and
health. The two descriptions most likely to overlap with broad business prose
were clarified:

- `nexus_get_opportunities` means current opportunity records already present in
  Nexus; it does not generate ideas or evaluate hypothetical businesses.
- `nexus_get_business_state` means current governed company operational state;
  it is not general advice, strategy, market research, or hypothetical idea
  evaluation.

No global Nexus-selection instruction, active-domain state, stale referent, or
unconditionally injected Nexus result was found in the tested session.

## Outcome

`OVERBROAD_NEXUS_TOOL_DESCRIPTIONS=PARTIAL_BEFORE_REPAIR; CLARIFIED`

`NEXUS_RESOURCE_SCOPE_TOO_BROAD=YES` for the two ambiguous descriptions before
repair; `NO` after repair.

`RESOURCE_ORDER_BIAS=UNKNOWN`: registration order exists, but the two native
reproductions selected different Nexus capabilities and did not establish order
as causal.

The descriptions remain usable for explicit questions such as current Nexus
opportunities or company state. No Nexus access was removed.

