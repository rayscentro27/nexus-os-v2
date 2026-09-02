# WP9L Tool-loop Forensics

## Root cause

`TOOL_LOOP_FAILURE_STAGE=MODEL_TOOL_SELECTION_AND_FOLLOWUP`.

`TOOL_LOOP_ROOT_CAUSE=YES`: the Oracle API lane exposed the generic Hermes
`delegation` wrapper alongside deferred MCP tools. The Nemotron route first
emitted `tool_call` for `nexus_delegate_specialist`; Hermes rejected it because
the target was directly callable. Subsequent attempts emitted missing arguments
or malformed wrapper JSON. A forced direct retry reached the model/provider
loop but ended with `Upstream idle timeout exceeded` after three retries.

After removing only the API-lane `delegation` toolset and restarting the
existing container, Hermes directly completed the specialist call. Receipts
`nexus-delegation-c9fa6d419fd64cc2aa66cac44f15f214`,
`nexus-delegation-2ec361e7729d472183ba9f13f802f081`,
`nexus-delegation-cf7c82ead4e7466aa964d15a5d3af3ad`,
`nexus-delegation-b1e984a697b74bb4828e3f4c44060c34`, and
`nexus-delegation-7d280d068a4a4b47ba597e752093625a` are real current SYSTEM
delegation receipts.

The sequential read probe also completed: reviews then work-items were read
and synthesized. Multi-specialist and continuity probes later timed out at the
declared 120-second boundary and remain unproven.
