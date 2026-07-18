# Nexus Top Repo Pattern Library

Generated: 2026-07-18

This library documents architecture and workflow patterns only. It does not copy external source code and does not approve any dependency.

| Source project | Problem solved | Pattern summary | Why it may help Nexus | Existing Nexus overlap | Security implications | License implications | Recommendation | Future wave |
|---|---|---|---|---|---|---|---|---|
| Stripe Samples | Payment checkout | Hosted checkout -> signed webhook -> local order state | Confirms Nexus should keep webhook-backed access | Certified test-mode Stripe path | Payment secrets server-side only | MIT metadata | Study only | Revenue hardening |
| Hyperswitch | Payment routing | Processor abstraction and failover | Useful only at scale | Current Stripe-only path is enough | Payment processor sprawl | Apache-2.0 metadata | Study architecture | Later |
| Kill Bill | Billing lifecycle | Subscription states, invoices, dunning | Future membership sprint | Current one-time order/fulfillment | Billing complexity | Apache-2.0 metadata | Defer | Subscription sprint |
| Paperless-ngx | Document processing | Document intake, classification, OCR lifecycle | Improves document queue/retention model | Nexus has private uploads/parser | Untrusted file parsing risk | GPL-3.0 metadata | Study only | Knowledge/doc wave |
| MarkItDown | File normalization | Convert files to Markdown/text | Helps bounded document/research ingestion | Existing parser scripts | Sandbox required for files | MIT metadata | Defer, possible dependency after sandbox | Knowledge/doc wave |
| Crawl4AI | Web extraction | Controlled public web extraction | Could support Alpha public research | Existing URL-review foundation | Prompt injection, robots/terms, cost | Apache-2.0 metadata | Defer | Repo-intelligence lane |
| Firecrawl | Web extraction service | API-backed crawl/extract | Existing Alpha URL-review reports mention it | URL-review function scaffold | Paid API, prompt injection, privacy | License and service terms require review | Defer | Repo-intelligence lane |
| LangGraph | Agent workflows | State graph, checkpoints, HITL interrupts | Useful pattern for governed orchestration | Hermes deterministic routers exist | Framework adds tool surface | MIT metadata | Study architecture only | Wave 2 |
| CrewAI | Role-based agent work | Crew/role/task separation | Department/workforce naming pattern | Existing departments and agent registry | Multi-agent autonomy risk | MIT metadata | Study architecture only | Wave 2 |
| Pydantic AI | Typed agent outputs | Structured outputs, providers, eval discipline | Good pattern for Hermes/Alpha adapters | TS schemas/tests exist | Provider/data leakage risk | report says MIT; exact version verify | Study concepts | Wave 3 |
| Letta | Long-lived memory | Memory blocks and promotion | Helps separate memory from knowledge | Hermes memory configs exist | Self-modifying memory risk | report says Apache-2.0; exact verify | Study concepts | Wave 3 |
| n8n | Visual automation | Triggers, nodes, credentials, workflow runs | May inspire capability graph | Nexus scripts/feeders exist | External side effects and credential sprawl | `NOASSERTION` metadata; source-available concerns | Defer/reject install | Wave 4 |
| Huginn | Agent automation | Event-driven agents | Automation pattern reference | Nexus has feeders/schedulers | Autonomous side effects | MIT metadata | Study only | Wave 4 |
| Metabase | Analytics dashboards | Query builder, saved dashboards | Founder Mode metrics UX reference | System health/revenue panels exist | SQL exposure if embedded poorly | `NOASSERTION` metadata | Study only | Wave 1/2 |
| Plausible | Privacy analytics | Minimal privacy-first analytics | Useful customer/revenue analytics pattern | Current reports only | Tracking consent and privacy | AGPL-3.0 metadata | Study only | Wave 5 |
| Chatwoot | Support operations | Inbox, conversations, assignments | Customer support workflow pattern | Admin communication surfaces exist | Customer PII and external messaging | `NOASSERTION` metadata | Study only | Wave 5 |
| Twenty | CRM | Object model, kanban/list/detail | Client pipeline/admin detail reference | Nexus ClientsPanel exists | Customer PII boundaries | `NOASSERTION` metadata | Study only | Wave 5 |
| ERPNext | ERP workflows | Broad departments, approvals, docs | Long-range operating-company reference | Nexus departments/workflows exist | Large app scope | GPL-3.0 metadata | Study only | Wave 6 |
| LEAN | Trading research/backtest | Algorithm framework and risk concepts | Trading lab research reference | Trading scripts/reports exist | Broker/live-trading risk | Apache-2.0 metadata | Study only | Trading later |
| vectorbt | Backtesting | Vectorized research/backtests | Offline research possible | Existing backtest reports | Finance risk and dependency review | `NOASSERTION` metadata | Defer | Trading later |

## Pattern decisions

- Adopt patterns, not code, for Wave 1.
- Prefer internal deterministic adapters before heavy frameworks.
- Use Ray Review for any repo-intelligence candidate that moves from research to dependency proposal.
- Keep Alpha separate and blocked from Supabase/client data.
