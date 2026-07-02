# Hermes Activation Levels

**Generated:** 2026-07-01
**Purpose:** Define 7 activation levels that control how every Hermes message is processed.

## Level Definitions

### Level 0: Safety Gate
- **Trigger:** publish/send/trade/charge/dispute/delete/run shell/start scheduler/live client write
- **Route:** `blocked_or_gated`
- **Model:** `no_model`
- **Source:** safety_gate
- **Description:** Execution verbs blocked. Requires Ray Review approval gate. Model not used unless drafting an approval summary.

### Level 1: Meta/Status/Cost/Process/Local Facts
- **Trigger:** model/cost/sections/processes/reports/settings/today/capability/routing trace questions
- **Route:** `no_model`
- **Model:** `no_model`
- **Source:** local_reports_usage_ledger_activity_journal_capability_state
- **Description:** Answerable from local reports, usage ledger, activity journal, capability state. Never triggers a model call.

### Level 2: Live Supabase Retrieval
- **Trigger:** approvals, business opportunities, clients, research rows, monetization, Ray Review, live records
- **Route:** `supabase_query`
- **Model:** `no_model`
- **Source:** live_supabase_first
- **Description:** Queries authenticated Supabase tables. Falls back to static with honest labeling. Stores results in conversation memory.

### Level 3: Conversation Memory / Follow-up Resolution
- **Trigger:** number 3, that one, pick one, do that, how do we implement it, monthly subscription, named entity
- **Route:** `conversation_memory`
- **Model:** `local_reasoning`
- **Source:** previous_ranked_listed_selected_items
- **Description:** Resolves follow-up references from previous ranked/listed/selected items. Never asks generic clarification when memory exists.

### Level 4: Local Reasoning
- **Trigger:** recommend, prioritize, what should I do next, fastest money move, implementation plan, business strategy
- **Route:** `local_reasoning`
- **Model:** `local_reasoning`
- **Source:** supabase_page_context_reports_memory
- **Description:** Local reasoning from Supabase + page context + reports + memory. Model is NOT used unless local reasoning is insufficient.

### Level 5: Model Reasoning
- **Trigger:** deep synthesis, polished writing, complex strategy, multi-source analysis
- **Route:** `model_reasoning`
- **Model:** `cheap_model`
- **Source:** packed_context_cost_logged
- **Description:** Model reasoning with packed context and cost logging. Only activates when Level 4 local reasoning is insufficient.

### Level 6: Approval/Action Layer
- **Trigger:** create review card, prepare task, send to specialist, run dry-run, external action
- **Route:** `approval_gated_workflow`
- **Model:** `no_model`
- **Source:** task_requests_ray_review
- **Description:** Action queued through Ray Review approval workflow. No direct execution.

## Routing Rules

1. **Level 0 overrides all:** Safety gate is checked first and overrides everything.
2. **Trace before memory:** Routing, source, Supabase/model-use, and domain-debug questions use the last non-trace routing record before any ordinal or selected-item memory check.
3. **Topic boundary before Level 3:** Casual/identity, meta/status, and explicit domains are classified before memory eligibility. Level 3 requires an explicit reference, named entity match, or clear same-domain continuation.
4. **Level 4 before 5:** Local reasoning is always tried before model reasoning to minimize model usage.
5. **Model never for status:** Level 1 questions never trigger a model call.
6. **Model never for cost:** Cost/token questions never trigger a model call.
7. **Supabase first:** Level 2 always tries live Supabase before falling back to static data.

## Activation Level Detection Order

```
1. Level 0: Safety gate (execution verbs)
2. Level 1: Routing/source/debug trace status
3. Level 1: Casual/identity local conversation
4. Level 1: Meta/status/cost/process/capability
5. Explicit domain classification and topic-boundary evaluation
6. Level 3: Eligible follow-up memory
7. Level 2: Live Supabase retrieval when records are required
8. Level 4: Domain/local reasoning
9. Level 5: Model reasoning when genuinely required
10. Level 6: Approval/action layer
11. Default: Level 4 only for current page context, otherwise Level 1
```
