# Nova/Nexus Conversation Intrusion Forensics

Campaign: `HG-WP6.6-LANGFUSE-NOVA-NEXUS-RESOURCE-BOUNDARY-AND-CONVERSATION-CENTER-FORENSICS-20260901-01`

## Finding

The live casual failures did not execute Nexus MCP. Receipts for `good morning`,
`my favorite is hazelnut`, and the morning question show zero tools. Their Nexus
content came from the same session's plain assistant history, which retained
earlier Nexus answers as ordinary conversational text.

The more specific defect was in `turn_requirements`: any prior Nexus result made
the latest Nexus capability a referent for every subsequent prompt. That caused
unrelated prompts to receive current-referent guidance and scoped Nexus tools.

## Live evidence

Session: `nova-telegram-primary-1288928049`

| Turn | Trace | MCP calls | Result |
|---|---|---:|---|
| good morning | `c95600fdeee1d38cfefdce72d25e421a` | 0 | Nexus health reused |
| do you drink coffee | `c03bb8795d58e6a87498b17db1752d7e` | 0 | natural |
| my favorite is hazelnut | `486c45a77c0c7b9a0b34d1c616a5a90e` | 0 | Nexus health reused |
| best way to start your morning | `d40360958bfa33dd54eb843bbcc64ea1` | 0 | Nexus work/operator framing |

The dedicated profile was active and the traces show no old brain or shadow MCP
execution. This is a session-context/referent-boundary defect, not a Nexus truth
defect.

## Root cause

`PRIOR_TOOL_RESULT_SALIENCE` and `OVERSTICKY_REFERENT_STATE` were proven. The
session sidecar retained resource-backed answers in `recent_turns` without
provenance, while referent metadata was not limited to anaphoric continuation.
The tool list being available was not itself sufficient to explain the claims;
the causal evidence is the zero-call traces plus the model-visible history.
