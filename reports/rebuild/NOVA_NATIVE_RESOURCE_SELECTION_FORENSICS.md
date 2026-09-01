# Nova Native Resource Selection Forensics

Campaign: `HG-WP7.1-NOVA-NATIVE-RESOURCE-SELECTION-SALIENCE-AND-NEXUS-BOUNDARY-COMPLETION-20260901-01`

## Evidence

The controlled current Hermes-native run used the dedicated Nova profile with
Nexus, Google, Web, and Alpha surfaces available. It had no prior resource
referent and no injected Nexus result. The self-contained prompt
`I have an idea for a new cleaning business. What should I evaluate first?`
selected one Nexus MCP capability. The first reproduction selected
`nexus_get_business_state`; after the scope clarification, a second
reproduction selected `nexus_get_opportunities`. In both runs the final answer
was ordinary cleaning-business evaluation advice and did not depend on the
returned Nexus state.

This proves a native model selection, not stale referent contamination. The
persisted session sidecar showed a newly-created Nexus referent only after the
call; no prior active referent existed before selection. No legacy shadow read
was enabled.

## Classification

`STALE_RESOURCE_REFERENT_CAUSED_SELECTION=NO`

`ROOT_CAUSE=MODEL_VOLUNTARY_BUT_UNNECESSARY_SELECTION`, with a contributing
tool-name/description salience risk. The response was not materially distorted,
so this is `UNNECESSARY_BUT_HARMLESS_TOOL_USE`, not a new Nova reasoning defect.
The model is still capable of native business reasoning; forcing zero calls
would require a prohibited router or behavioral restriction.

## Architecture conclusion

The safe repair boundary was MCP metadata: opportunity records already present
in Nexus are now explicitly distinguished from idea generation, hypothetical
business evaluation, market research, and general strategy advice. The
`business_state` description likewise identifies current governed operational
state and excludes general advice. No profile, SOUL, routing, tool
availability, or conversation behavior was changed.

