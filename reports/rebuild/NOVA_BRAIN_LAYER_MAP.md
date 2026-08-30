# Nova Brain-Layer Freedom and Truth Audit

Campaign: `HG-WP6.5-NOVA-BRAIN-LAYER-FREEDOM-CAPABILITY-AND-TRUTH-AUDIT-20260830-01`

## Audited live layers

| Layer | Live source | Effect | Refusal risk |
|---|---|---|---|
| Telegram ingress | `scripts/nova/nova_telegram_worker.py` | Authenticates and dispatches Nova; contains legacy fixed error text for missing repair state | Medium; operational errors can become user-facing retrieval refusals |
| Nova graph | `scripts/nexus_agent_platform/agents/nova.py` | Classifies, selects bounded capabilities, builds context, calls model, validates output | High; fallback and pre-model gates can terminate before model/tool reasoning |
| Shared capability boundary | `scripts/nexus_agent_platform/capabilities/shared.py` | Enforces read allowlist and governed intake; no Nova direct writes | Appropriate; must not be presented as conversational inability |
| Domain policy | `scripts/nexus_agent_platform/domain_source_policy.py` | Selects sources by subject domain | Medium if a global Nexus-first rule is reintroduced |
| Truth view/quarantine | `nova_truth_view.py`, `report_quarantine.py` | Adds provenance and blocks legacy/synthetic current truth | Appropriate; unavailable evidence must remain UNKNOWN |
| Company context | `nova_company_context.py` | Compact derived context for company questions | Medium; daily brief is context, not authority |
| Web adapter | shared `public_web_search` → existing `hermes_web_search` provider chain | Bounded public read/search, provider and failure provenance | High if provider failure is rendered as all-system failure |
| Alpha | `alpha_research.py`, `alpha_evidence_bridge.py` | Structured research jobs and bounded evidence path; current fresh handoff is intake-only | Medium; request submission must be distinguished from execution |
| Nexus delegation | `nexus_command_acknowledgement.py` | RECEIVED acknowledgement and durable governed queue record | Appropriate; Nova submits, Nexus authorizes/executes |
| Model/fallback | Nova model call and `_build_fallback_response` | Natural synthesis or honest bounded fallback | High when generic refusal templates replace service-specific facts |

## Findings

The principal defect is not a broad Nova personality rule. It is a layered
failure mode: capability errors and stale operational context are allowed to
reach response generation without a service-specific envelope, while some
read paths were historically described as “read-only” in language that can be
misread as “cannot communicate or research.” `general_search` is an approved
Supabase-table search, not public web search; public research now has a distinct
`public_web_search` capability and contextual free-research follows that path.

Truth discipline remains intentionally strict: configured is not running,
legacy/synthetic reports are not current truth, and failed reads remain
UNKNOWN. A failed dependency must not disable unrelated domains. Direct Nexus
mutation/execution remains unavailable to Nova, while bounded request intake is
allowed. Alpha request intake is bounded and does not claim that research ran.

## Live capability status

| Capability | Implemented | Development-tested | Real-world status |
|---|---:|---:|---|
| Ordinary conversation | yes | yes | requires fresh Telegram proof |
| Nexus canonical reads | yes | yes | bounded; fresh live Telegram proof required |
| Public web search | yes via existing provider chain | yes | not certified by this audit |
| Page retrieval/verification | existing Alpha evidence adapter | partial | not proven as live Nova E2E |
| Alpha request intake | yes, governed `RECEIVED` | added/targeted | not research execution proof |
| Nexus request intake | yes, governed `RECEIVED` | yes | not operational execution proof |
| Direct Nexus execution | no | authority regression retained | prohibited |

No manual Telegram invocation or certification evidence was created by this
audit. Fresh real Telegram tests are required.
