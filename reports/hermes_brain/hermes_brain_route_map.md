# Hermes Brain Current Route Map

The priority below is source order in `routeHermesPriority`; each match returns immediately. Several rows represent a family with multiple adjacent checks.

| Priority | Route | Matching logic | Renderer | Data/context | Fallback / weakness | Representative tests |
|---:|---|---|---|---|---|---|
| 1 | `safety_gate` | Risky execution verbs plus trade/publish/charge/deploy/delete/send/scheduler targets | Inline safety text | Safety policy only | Regex misses semantic variants; intentionally no execution | route decision, model routing, cross-route regression |
| 2 | `trace_source_meta` | `classifyTraceQuestion` source/route/memory/why variants | `answerHermesTraceQuestion` | Last non-trace routing trace | Natural phrase coverage incomplete; trace module-local | real transcript, common advisor, route policy |
| 3 | `cost_model_usage_status` | Trace model kind or broad model/token/cost terms | Trace/capability handler | Last trace/capability registry | Keyword risk around “model”; product exception is separate and fragile | model status/project, model usage ledger |
| 4 | `explicit_domain_retrieval` | Protected approvals, opportunities, clients, research inventory syntax | `buildLiveSupabaseContext`; opportunity list wrapper | Supabase session/RLS; hardcoded offer list fallback | Narrow grammar; generic row output; hardcoded selection rows | cross-route regression, live context |
| 5 | `schedule_action_prepare` | Schedule/create recurring report/reminder/audit patterns | Inline draft/block text | Local policy; no actual report read | No structured schedule; narrow time/target parser | common advisor polish |
| 6 | `approval_action_prepare` (implementation) | Start/build/implementation/file task patterns | Inline gated implementation response | Approval policy | Not a structured Ray Review task | model status/project |
| 7 | `system_health_report` | Exact phrases such as `what is system health`, `show system health`, `what is broken` | `answerSystemHealthQuestion` | Capability registry, section registry, hardcoded checkpoint | `how is the system health` misses; checkpoint text may be stale | route-dominance repair |
| 8 | `page_connection_status`, `page_context_status` | Specific page/website visibility questions | `answerPageContextQuestion` | Passed UI metadata | Metadata is not page data; must not imply live read | route-dominance tests |
| 9 | `process_activity_status` | Activity/work completion classifier unless advisory follow-up | Activity status renderer | Activity journal/checkpoint | Evidence freshness not uniform | conversational gaps |
| 10 | `fallback_continuation` | Exact option reply while fallback state alive | Inline continuation renderer | Fallback state, optional static long-term context | Offered labels and accepted labels disagree (`Nexus build plan` vs `Nexus`) | model status/project |
| 11 | `casual_common` | Greeting, human-experience, common preference without domain terms | `answerCasualCommonQuestion` | None/common knowledge | Some responses mention Nexus/progress; domain-term exclusions are keyword based | common advisor, conversational gaps |
| 12 | `nexus_build_planning` | Build/design CRM/portal/dashboard/workflow for Nexus | Inline Nexus plan | Static product assertions/local reports allowed but not read | Claims foundation from static text rather than evidence packet | model status/project |
| 13 | `general_project_planning` | Plan/build general app/house/project | General project renderer | Plain reasoning | Limited entity coverage | model status/project |
| 14 | `general_advisor` | Product entity or recommendation patterns | General advisor renderer | Plain reasoning; long-term packet permitted | “Current” recommendations do not retrieve; broad/no typed advisory contract | advisory/product, common advisor |
| 15 | `opportunity_aware_recommendation` | Recommendation/physical-world opportunity classifier | Opportunity advisor | Local reasoning framework | May introduce monetization when user wants only practical advice | opportunity-aware tests |
| 16 | `casual_identity` | Domain classifier returns casual identity | Conversation brain | None | Overlap with product/common route; mostly superseded | brain pipeline |
| 17 | `capability_status` | Capability/web/database/model status phrases | Capability registry | Local environment-derived registry | `connected to` can conflict with page questions and Supabase trace language | pipeline, intent router |
| 18 | `process_settings_reports_status` | Status/inventory words in settings/reports/tools/system/automation/research; trading status | Specialized trading/report/daily branches, otherwise generic `local_status` | Local reports permitted | Main contract failure: permitted evidence is not read; research/system questions get policy prose | route dominance audit |
| 19 | `approval_action_prepare` (draft) | Create/prepare/queue Ray Review/task/dry run | Selection resolution plus inline local draft | Selection memory, approval policy | No specialist handoff route; no persisted draft | route policy, common advisor |
| 20 | `approval_action_prepare` (vague action) | Action verb plus this/that/it | Selection resolution or target clarification | Selection memory | Over-broad verbs; “handoff” without pronoun not captured | conversational gaps |
| 21 | `explicit_domain_retrieval` (generic) | Domain known plus inventory wording | Supabase or local inventory handler | Domain-dependent | Normal `do we have any clients` grammar is missed | route regression tests cover only selected forms |
| 22 | `memory_followup` | Explicit ordinal/pronoun/named selection | Selection implementation/recommendation | Selection memory and duplicated conversation lists | Expiry field not enforced by getter; retrieved rows are not retained | pipeline/topic-boundary tests |
| 23 | `revenue_reasoning` | Revenue strategy classifier | Revenue reasoner | Static long-term context; optional Supabase | Source fusion not item-level; advisory contract implicit | opportunity recommendation tests |
| 24 | `advisory_followup` | Live advisory state plus narrow follow-up phrases/domain guard | `answerAdvisoryFollowUp` | Advisory state attached via long-term flag | Loses continuity after six turns; template relevance not explicitly verified | advisory continuity, cross-route tests |
| 25 | `local_reasoning` | Any known domain or recommend/plan/strategy terms | Trading/recommendation/client/generic inline branches | Static/local context permitted | Generic allowed-context renderer overrides unanswered direct questions | numerous route tests |
| 26 | `model_reasoning` | Deep synthesis/compose/polished keywords | `hermesModelChat` | Model and policy-packed context | Ordered after broad known-domain reasoning, so many synthesis requests never reach it; may invoke paid provider if configured | model routing |
| 27 | `fallback_clarification` | No earlier match | Fixed clarification options | None; stores fallback continuity | Missing intent looks like user ambiguity; generic fallback dominance | fallback continuity tests |

## Route-to-source observations

- Retrieval policy is declarative, but only route handler code decides whether a read happens.
- `local_reports` often means “allowed” rather than a concrete report adapter invocation.
- The opportunity route combines hardcoded normalized offers with live query prose; it does not map returned rows into selection memory.
- Route confidence defaults from the decision factory rather than classifier evidence and is not a calibrated probability.
- The older `hermesIntentRouter`, `hermesResponseRouter`, and `hermesOrchestrator` remain in the repository and tests, creating conceptual split-brain even though current UI surfaces use `hermesBrainPipeline`.
