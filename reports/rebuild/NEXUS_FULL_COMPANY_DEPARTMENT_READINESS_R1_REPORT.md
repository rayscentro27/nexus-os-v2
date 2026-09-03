# Nexus Full Company Department Readiness R1

Generated 2026-09-03 from repository and persisted-runtime evidence. This
report inventories what exists; it does not treat a UI label, synthetic seed,
or specialist name as proof of a complete autonomous department.

## Executive Result

`FULL_COMPANY_DEPARTMENT_READINESS_R1=PARTIAL`.

Nexus has a real operating foundation: Hermes coordination, Research and Alpha
intelligence, a capability broker, governed work orders, evidence-backed
verification, Ray gates, launchd/runtime processes, and department operations
read models. The company is not yet a complete cross-department organization.

The central finding is a registry/reality mismatch. The active TypeScript
department operations registry exposes five operational departments. The
persisted Python-facing registry exposes seven legacy groups. The specialist
registry exposes nine specialists. These are overlapping views, not three
independent companies, but they do not yet form one canonical machine-readable
map for all required departments.

No kernel, Research scheduler, WP9, or GoClear product redesign was performed.
No true external blocker was encountered.

## Existing Company Organization

### Authoritative layers found

| Layer | Evidence | What it actually provides |
|---|---|---|
| Active department operations | `src/lib/departments/departmentOperations.ts` | Five typed department definitions, queues, blockers, incidents, verification, health, and Ray-review drafts; queue data is explicitly synthetic |
| Legacy durable route registry | `data/runtime/nexus_department_registry.json` | Seven route groups used by `scripts/nexus_agent_platform/department_router.py` |
| Specialist registry | `configs/specialist_registry.json` | Nine named specialist roles and safe/blocked actions |
| Capability OS | `configs/nexus_capability_manifest.json`, `src/lib/capabilities/capabilityRegistry.ts` | Capability ownership, data classes, risk, approval, executor, receipt, and availability |
| Hermes routing | `src/lib/hermes/hermesWorkRouter.ts`, `src/lib/nexusAgentDispatch.ts`, Python department router | Intent/work routing and safe fallbacks; execution is registry-validated |
| Durable Research | `data/runtime/research_heartbeat.json`, Research runtime reports | Active heartbeat, scheduler, durable owner, next wake, and evidence loop |
| Runtime processes | `launchd/`, `data/operations/nexus_process_registry.json` | Hermes/Nova/Telegram/voice/research-related process declarations and health receipts |
| UI/read model | `src/components/DepartmentOperationsWorkspace.tsx`, Hermes tools | Read-only department list/status/queue/blocker/approval views |

### Canonical logical map for buildout

The following map reconciles aliases without creating parallel systems:

| Canonical department | Existing implementation/alias | Current readiness |
|---|---|---|
| Research | `research` / legacy `RESEARCH_ALPHA`; `research_intelligence` and live Research runtime | READY |
| Alpha | Alpha files under `src/hermes/alpha`; Alpha review artifacts and bridge | PARTIAL: capability is present; always-on registered department/runtime is not complete |
| Hermes Nova | Hermes executive/runtime layers, Nova launchd/Telegram/shadow runtime | PARTIAL |
| Systems Engineering | `engineering` / legacy `SYSTEM_ENGINEERING`; `system.*`, `frontend.build`, `tests.run`, repo intelligence | PARTIAL |
| Creative | Creative intelligence, marketing asset studios, visual critic, creative feeder | PARTIAL |
| Marketing | `marketing` specialist, marketing asset studio, content feeder, draft connector | PARTIAL |
| SEO | SEO keyword scout, SEO feeder, Alpha SEO opportunity engine | PARTIAL |
| Clyde Credit | `credit` specialist, Clyde context/credit strategy/readiness engines, credit/funding combined operations | PARTIAL |
| Funding | `funding` specialist, funding readiness/research engines, combined credit/funding route | PARTIAL |
| Finance | finance scripts, revenue/cost receipts, finance specialist capability is not a complete department | PARTIAL |
| Business Opportunity | opportunity desk, business opportunity feeder, Alpha opportunity brain | PARTIAL |
| Trading Research | trading lab, forex research capability, paper/demo policy and feeder | PARTIAL; live/funded execution prohibited |

### Legitimate additional departments/cells

Operations, Knowledge, Governance/Review, Client Lifecycle, Monetization,
Automation, and Client Success already exist as operational groups or
specialist cells. Operations/Knowledge/Governance are important control-plane
departments. Monetization, Automation, and Client Success currently behave
more like specialist capabilities than fully independent cross-company
departments.

## Department-by-Department Audit

| Department | Primary agent / specialists | Inputs → outputs | Runtime, persistence, tools, tests | Dependencies / authority / gaps |
|---|---|---|---|---|
| Research | Research Lead; `research` specialist | approved questions/source gaps → sourced findings, provenance, follow-up work | Durable Research owner, heartbeat/scheduler, live-web runner, repo intelligence, reports/runtime; Research tests and receipts exist | Depends on approved sources, Alpha review, TruthKernel. Read-only; no client PII. Gap: logical department mapping is split between registries |
| Alpha | Alpha review brain; Alpha provider/research/URL/opportunity/trading modules | research candidates/results → quality scores, deficiencies, follow-up | `src/hermes/alpha/*`, Alpha artifacts, bridge and tests | Read-only/review; Ray for consequential recommendation. Gap: optional runtime says Alpha not registered/always-on in current health receipt |
| Hermes Nova | Hermes executive coordinator; Nova shadow/Telegram/voice workers | objectives, status, department requests → briefs, routing, review packets | Hermes runtime, Nova launchd/shadow sessions, conversation/router tests | No consequential authority. Gap: one public-facing operator contract across chat/portal/Telegram/voice remains incomplete |
| Systems Engineering | Engineering Lead; automation/model-routing specialists | failures, code, capability gaps → bounded repairs, tests, recommendations, receipts | Capability manifest, Python/CLI runners, build/test tooling, engineering reports | Internal code/test work allowed; deploy/production mutation gated. Gap: full department contract not shared with all logical departments |
| Creative | Creative Lead implicit; creative intelligence, visual critic, creative studio feeder | verified brief → concepts, scripts, visual directions, QA receipts | `creative.intelligence`, `visual.critic`, creative studio modules, creative tests | Draft-only/public release gated. Gap: no complete production/distribution/result loop |
| Marketing | Marketing specialist; monetization and content studios | research/offer → messaging, content, funnel and campaign drafts | Marketing asset studios, drafts, content policy, draft connector | Draft-only; publish/send gated. Gap: no real acquisition execution/measurement loop |
| SEO | SEO Lead implicit; keyword scout, SEO opportunity engine | search evidence → keyword/page/internal-link plans | `seoKeywordScout`, SEO feeders/docs, research inputs | Research/read-only; publication gated. Gap: no connected Search Console/result feedback |
| Clyde Credit | Credit Workflow Lead; credit specialist, Clyde engines | approved aggregate/client context → readiness analysis/checklists | Clyde context, credit strategy/readiness engines, portal UI, synthetic queue | No client PII in Research; client-facing recommendations gated. Gap: production client data/tenant-safe workflow incomplete |
| Funding | Funding Lead; funding specialist | readiness evidence → lender/grant preparation and review plan | Funding readiness engines, checks, research, combined registry route | Application submission prohibited; Ray review required. Gap: no governed application/approval workflow with real client authority |
| Finance | Finance Lead implicit; monetization/finance scripts and ledgers | costs, revenue events, opportunities → economic controls, ledgers, allocation analysis | finance scripts, revenue/cost receipts, value ledgers | No transactions/spending autonomously. Gap: no complete finance department registry/agent/feedback contract |
| Business Opportunity | Opportunity Lead implicit; opportunity desk/brain/feeder | research/market evidence → scored opportunities, plans, validation requests | Alpha opportunity modules, opportunity feeder, persisted opportunities/outcomes | Validation and external action gated. Gap: market validation and revenue outcome integrations absent |
| Trading Research | Trading Research Lead; trading lab/forex modules | approved market data/strategies → paper research/backtests/hypotheses | `forex.research`, trading lab, paper-only policies/feeders | Paper/demo only; funded/live capability prohibited. Gap: no universal department contract and no live economic outcome by design |

## Cross-Department Contract

The existing shared primitives are sufficient for a bounded contract:

`Hermes objective → department route → Capability OS preflight → bounded work
order → evidence/receipt → verification → objective update → next action`.

The TypeScript operations model exposes typed queue items, dependencies,
blockers, incidents, work verification, execution plans, and health. The
Python router validates loop, skill, worker, and department membership before
execution. Hermes delegation policy distinguishes safe internal jobs,
approval-gated jobs, and blocked jobs.

`CROSS_DEPARTMENT_WORK_CONTRACT=PASS_REAL` at shared-contract level.

Coverage is incomplete: the active operations registry does not yet register
all twelve logical departments, and queue seeds are synthetic. That is a
readiness gap, not permission to invent work or claim all departments are
operational.

## Research Intelligence Integration

Research is already a durable universal service for the implemented routes:
Research requests are represented through Hermes/Alpha adapters, live public
research is bounded and provenance-aware, and Research continues while queues
are empty or between cycles.

For the complete company map, the expected interface is:

`department → knowledge gap → Research request → Alpha challenge → qualified
result → department resumes`.

Research and Alpha satisfy this path for existing research/opportunity,
systems, marketing/SEO, and trading lanes. It is not yet proven for every
logical department, especially Finance, Creative, and the split Clyde/Funding
aliases.

`UNIVERSAL_RESEARCH_SERVICE=FAIL` for full-company coverage; existing Research
itself remains `READY`.

## Result Feedback

The existing company pattern supports evidence receipts and objective updates,
and prior autonomy campaigns proved Research/result feedback for implemented
lanes. A single universal typed result envelope consumed by every logical
department is not present in the audited source.

Required completion path:

`department action → result envelope → Research interpretation → Alpha review
→ knowledge update → objective update → next action`.

`UNIVERSAL_RESULT_FEEDBACK=FAIL` for full-company coverage. This is the highest-
priority foundational contract before department-specific builds.

## Authority

The authority model is coherent and fail-closed:

| Class | Examples |
|---|---|
| `AUTONOMOUS_INTERNAL` | public read-only research, analysis, internal drafts, creative directions, safe code/tests, paper backtests, plans, reports, knowledge updates |
| `APPROVAL_REQUIRED_EXTERNAL` | public publishing, external outreach, spending, contracts, financial applications, payment activation, production promotion, client contact, client-facing recommendations |
| `SAFETY_BLOCKED` | funded/live trading, unapproved dispute/bureau contact, destructive production changes, secret exposure, client PII to public research |

`DEPARTMENT_AUTHORITY_MODEL=PASS_REAL`. Existing capability preflight,
TruthKernel/Ray Review, connector registries, and explicit blocked actions are
the evidence. Idle workers are not treated as unavailable; persistent services
may be `IDLE_BETWEEN_CYCLES` while `OPERATIONAL` and `READY`.

## Capability Gaps

| Gap class | Departments affected | Priority |
|---|---|---|
| Missing canonical registry mapping | all logical departments beyond the existing five/seven views | P0 |
| Missing universal request/result envelope | all cross-department routes | P0 |
| Missing runtime/agent registration | Alpha, Hermes Nova, Finance, Creative/Marketing/SEO specialist lanes | P1 |
| Missing real data/integrations | Marketing/SEO analytics, Finance revenue events, Clyde/Funding client-safe data | P1 |
| Missing external authority | publishing, outreach, payment, applications, production mutation | policy-controlled, not a defect |
| Missing complete tests | universal cross-department contract and department-specific result feedback | P1 |
| Missing UI/read model | full logical map, state contract, effective readiness per department | P2 |

No department is classified `MISSING`: each required lane has at least a
specialist, module, feeder, report, or adjacent capability. `PARTIAL` means
the lane exists but is not yet a complete independently routable department.

## Build Priority

1. **Foundational registry and contract:** reconcile aliases into one canonical
   organization map; add state/readiness fields and universal request/result
   envelopes without replacing the kernel or Research.
2. **Creative:** complete brief → concept → critic → asset metadata contract.
3. **Marketing:** connect verified research to offer/funnel/content drafts and
   measurable experiment definitions.
4. **SEO:** complete keyword → page brief → internal-link → governed publication
   and Search Console feedback path.
5. **Clyde / Credit readiness:** separate the logical Clyde credit role from
   Funding while retaining the existing combined safety boundary.
6. **Funding:** add governed strategy/application/approval workflow around
   approved readiness evidence; no submission authority by default.
7. **Finance:** formalize economic control, revenue/cost/value ledgers, and
   capital-allocation analysis without transaction authority.
8. **Business Opportunity:** connect discovery to validation evidence, plans,
   and outcome feedback.
9. **Trading Research:** retain paper/demo-only research and real-data
   provenance; do not build funded execution.
10. **Hermes Nova:** unify executive/operator presentation across chat, portal,
    Telegram, voice, and avatar after the service contracts are stable.

This preserves the requested strategic ordering while moving the shared
contract reconciliation ahead of department builds because it is a dependency,
not a cosmetic enhancement.

## Foundational Repairs

No production code repair was made in this campaign. The audited shared
operations primitives are present and changing the kernel or Research would
increase regression risk. The required foundational repair is identified and
bounded for the next phase:

- make one canonical department map the source for both TypeScript and Python
  routing;
- preserve legacy IDs as aliases rather than duplicate departments;
- add a common department state/readiness projection;
- add universal Research-request and result-feedback schemas;
- add contract tests for every canonical department, including authority,
  persistence, evidence, and next-action semantics.

The focused Python router suite ran 13 tests: 11 passed and 2 failed because
the current front-brain fallback returned `NO_EXECUTION`/`ANSWERED` where the
older tests expected `UNKNOWN_INTENT`/`BLOCKED`; logs also showed an empty
Bearer header. This is a pre-existing router/test semantic mismatch, not a
department capability proof, and needs a separate Systems repair. The focused
Vitest invocation did not complete after 60 seconds of Vite initialization and
was stopped; no test result was inferred from that run.

## Next Phase

`COMMERCIAL_ENGINE_CREATIVE_MARKETING_SEO`.

Before that build begins, implement the P0 canonical organization/request/
result contract and its contract tests. Then build Creative, Marketing, and SEO
against that one interface, keeping all public distribution and customer-facing
actions approval-gated.

## Git

Starting state: `START_HEAD=61f928f2df741f99d283cb2faf41bc6c881b0440`,
`origin/main=33c661559a37fcbda34adb98eb61c304fd793131`, branch `main`.
`WORKTREE_ENTRY_COUNT_BEFORE=10222`; 582 pre-existing status lines were
present. No reset, clean, broad staging, secret exposure, or unrelated change
was performed. This report is the only task-specific artifact.

## Final Contract

```text
FULL_COMPANY_DEPARTMENT_READINESS_R1=PARTIAL
RESEARCH=READY
ALPHA=PARTIAL
HERMES_NOVA=PARTIAL
SYSTEMS_ENGINEERING=PARTIAL
CREATIVE=PARTIAL
MARKETING=PARTIAL
SEO=PARTIAL
CLYDE_CREDIT=PARTIAL
FUNDING=PARTIAL
FINANCE=PARTIAL
BUSINESS_OPPORTUNITY=PARTIAL
TRADING_RESEARCH=PARTIAL
CROSS_DEPARTMENT_WORK_CONTRACT=PASS_REAL
UNIVERSAL_RESEARCH_SERVICE=FAIL
UNIVERSAL_RESULT_FEEDBACK=FAIL
DEPARTMENT_AUTHORITY_MODEL=PASS_REAL
DEPARTMENTS_READY=1
DEPARTMENTS_PARTIAL=11
DEPARTMENTS_MISSING=0
TRUE_RAY_BLOCKERS=NONE
NEXT_RECOMMENDED_PHASE=COMMERCIAL_ENGINE_CREATIVE_MARKETING_SEO
```
