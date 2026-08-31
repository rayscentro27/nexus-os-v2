# Nova Custom Stack vs Hermes 0.20.6

| Concern | Current Nova | Hermes 0.20.6 | Assessment |
|---|---|---|---|
| Identity/SOUL | Embedded `agents/nova.py` | Profile/system-prompt builder | Keep Nova identity; optionally express it through Hermes profile later |
| Model call | `LlmGatewayAdapter` → OpenRouter | Native provider adapters/model routing | Candidate for selective replacement |
| Provider fallback | Custom LiteLLM flag then OpenRouter | Native adapter/retry/failover surfaces | Candidate; must preserve cost policy |
| Tool request format | JSON marker in model text | Native provider tool calls | Strong duplication; native loop is cleaner |
| Tool dispatch | `validate_model_request` + shared capability executor | Registry + `handle_function_call` + tool executor | Keep Nexus boundary; expose bounded adapters to native registry if migrated |
| Tool continuation | Custom second prompt | Native tool-result continuation | Candidate for selective replacement |
| Sessions | Nova memory files/custom metadata | Gateway session store and prompt restoration | Duplication; migration requires stale-belief controls |
| Memory | Custom Nova memory and context filtering | Native memory manager + session search | Hermes can help, but durable/volatile separation remains required |
| Skills | Nova catalog/capability docs | Native skills index/skill tools | Candidate for capability description, not authority grants |
| Delegation | Custom Alpha/Nexus intake | `delegate_task`, workers, toolsets | Hybrid required for long-running governed work |
| Web | Shared Nexus capability adapters | `web_search`, `web_extract`, browser tools/registry | Hermes can host adapters; do not discard proven SearXNG/HTTP paths |
| Truth | Nexus TruthKernel/live receipts | No equivalent proven authority | Must remain custom |
| Authority | Nexus approval/work-order boundary | Tool guardrails/approvals | Must remain Nexus-owned |
| Cost | Nexus cost policy | Tool/provider config and approvals | Keep custom policy at invocation boundary |
| Privacy | Nexus data scope/PII controls | Tool sandbox/credential controls | Keep Nexus data policy; compose with Hermes tool scopes |
| Fallback | Custom `_advisory_fallback` without real tools | Native model/tool loop and provider errors | Candidate for replacement, but preserve truthful failure semantics |

## Custom components Hermes already supplies

- provider/model adapters and metadata
- native assistant tool-call parsing
- tool registry and execution loop
- tool-result continuation
- session persistence and prompt restoration
- memory/session search primitives
- skills and toolset discovery
- synchronous delegated workers/subagents
- browser/web tool surfaces

## Components that remain Nexus-specific

- TruthKernel and provenance/certification semantics
- governed live operational truth
- receipts and work-order lifecycle
- approval and authority validation
- client PII isolation and authorized Supabase reads
- cost policy for approved external services
- Nova-specific business context and role separation

