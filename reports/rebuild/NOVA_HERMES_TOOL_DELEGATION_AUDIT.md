# Hermes Tool and Delegation Audit

## Native tool loop

Hermes 0.20.6 has a registered-tool model:

```text
provider assistant tool_calls
  -> run_agent._execute_tool_calls
  -> agent.tool_executor / agent_runtime_helpers
  -> model_tools registry/handler
  -> tool result appended to conversation
  -> native continuation
```

Evidence: `run_agent.py:4065-4145`, `model_tools.py:488-570`, and the tool
registry. This is materially different from Nova's text marker parser at
`agents/nova.py:4394-4424`.

## Adapter fit

The following could be represented as Hermes tools without granting direct
execution authority:

| Resource | Native-tool fit | Required adapter |
|---|---|---|
| Public web search | YES | Wrap the existing approved search provider; return URLs, timestamps, provider, and failure metadata |
| Public page retrieval | YES | Wrap existing HTTP/browser retrieval; preserve URL/provenance and bounded content |
| Nexus read | YES | Read-only adapter that calls governed TruthKernel/read APIs; never expose arbitrary SQL or writes |
| Alpha research | PARTIAL | Use native delegation for short synchronous research; retain Nexus/Alpha intake for tracked long-running artifacts |
| Google read | YES | Granular read-only adapter; do not infer send/calendar-write authority |

## Delegation fit by work type

| Work | Best primitive | Reason |
|---|---|---|
| Short synchronous reasoning subtask | Hermes `delegate_task` | bounded child context and returned result |
| Long-running research artifact | Existing Alpha/Nexus intake plus worker | durable lifecycle, artifact, recovery, receipts |
| Persistent operational work order | Hermes Nexus governed work-order path | authority and execution belong to Nexus |
| Cross-agent handoff | Hybrid | Hermes can carry conversation/task context; Nexus/Alpha retain domain lifecycle |

## Failure behavior

Hermes can return tool errors into the model loop rather than forcing a user
response. A future adapter must still expose `retryable`, alternatives, cost,
privacy scope, and authority status. Hermes fallback alone must not bypass Nexus
approval or turn a provider failure into a generic refusal.

