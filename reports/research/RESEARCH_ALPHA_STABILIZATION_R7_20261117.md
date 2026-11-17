# Research / Alpha stabilization R7 — 2026-11-17

## Scope and workflow state

This pass stayed within the existing Research Room and Research R10 paths. Autonomous ingestion remains off; manual intake remains on. No Marketing or Creative work was started. The durable GoClear workflow `wf_dfccb523f5114f68a53e226b4c33f402` remains `RUNNING` at `BUSINESS_PLAN`; this pass did not dispatch or advance it.

## Search adapter repair

The built-in parser was receiving DuckDuckGo challenge HTML and, on some Bing responses, stopping before the result list. The HTML parser also discarded useful snippets and the previous relevance inputs contained generic terms. The repair keeps the relevance threshold, parses the existing result selectors and snippets, reads a bounded 120 KB response, and uses the same Bing provider's bounded RSS representation if HTML has no usable results. RSS and HTML candidates still pass through the existing relevance screen.

Live bounded search returned five usable results. The first result was the official SBA 7(a) page. A focused `SourceTools` run acquired a source after testing the Nexus route; a second run with a forced no-results first route acquired a source through the existing Hermes free-search adapter. The new candidate loop tries no more than three ranked URLs per provider, then continues the existing fallback chain.

Hermes targeted search returned five results under a fresh step-attempt child job. The prior egress exhaustion was consistent with retry attempts reusing the same idempotent child-job identity and exhausting its request allowance. Child-job identity now includes the Workflow step attempt. Each attempt remains capped at 20 requests, with a 2 MB response envelope; public page reads are capped and estimated at 400 KB.

## Known-page retrieval and durable evidence

The existing official SBA 7(a) URL was fetched through the governed public HTTP path. It returned the SBA page title and 7,708 characters. A bounded source-observation finding was persisted to the existing GoClear Research Room `rcase_d2efaff7a388ad7177`, reusing source ID `rr_sba_7a_20261117`; no duplicate source row was created.

Finding: `r7_source_evidence_81689ff075d6f8d2`. It records only what the retrieved page supports: listed 7(a) uses and key eligibility factors, with explicit limits against inferring any individual applicant's eligibility or approval. The source hash and short excerpts are persisted; the full page was not copied into a database field.

The page reader previously estimated and attempted 1 MB while the research child job allowed 500 KB, producing `JOB_BUDGET_LIMIT`. It now estimates and reads 400 KB, within the existing request envelope.

## Research MCP and model route

The existing Research MCP completed authenticated MCP initialization, discovered nine tools, and returned a successful read-only `research_health` result (`research` 1.28.1; R10 status `ok`). No Research job was created through MCP.

The canonical Agent Control Plane resolver reports `RESEARCH_DEEP=AVAILABLE` for Alpha. The last actual persisted Alpha run in the existing case used `gpt-6-luna`, selected by the existing strong-reasoning Research route. This pass did not change that profile or pin a provider. A fresh bounded AdvisorRouter assessment was attempted but could not complete: `CHATGPT_PLAN_ADVISOR_TIMEOUT` and OpenRouter HTTP 404. Therefore this pass adds primary-source evidence to the prior Alpha analysis and fact-check, but does not claim a new Alpha-generated conclusion.

## Contabo REA canary

The existing SSH-only REA wrapper accepted and ran a bounded `TOOL_CERT` request against the public SBA URL and returned a result. The harness result was not a browser research pass: `harness_tool_layer=FAIL`, `tool_call_count=0`, no screenshot, and `REA_BROWSER_INSPECTION.pass=false`. No paid model request, login, download, form action, or external side effect was performed. The wrapper is callable; public-page browser execution is not certified by this canary.

## Room-link correction and preserved probe

The initial integrated diagnostic called `deep_research` with a changed objective. The Research engine's objective-key lookup opened a separate case despite the workflow already holding an explicit `research_room_id`. The case `rcase_ea5201bc07f1ad3b98` is retained with its failed attempt history and marked `PARKED_DUPLICATE_PROBE` in its room state, pointing to the canonical room. The existing Research stop-policy intercepted a top-level `PARKED` transition and kept its case status `REPLANNING`; it was not deleted or force-closed. A code and contract-test fix now makes `ensure_room` reuse the workflow's explicit room link, and fails closed if that linked case is missing.

## Tests and code changes

Focused tests cover search HTML/RSS parsing, candidate fallback after an unreadable first result, governed page-size limits, per-attempt research child jobs, workflow-linked room reuse, and Supabase lease renewal used by the existing REA handoff. Python compilation passed for the touched runtime/test modules. No deployment or service restart was performed.

## Remaining limitations

- Fresh Alpha assessment remains unavailable while the existing ChatGPT Plan route times out and the configured free OpenRouter route returns 404.
- The Contabo REA wrapper is reachable, but the actual browser canary returned zero tool calls and no screenshot.
- The separate diagnostic case remains top-level `REPLANNING` because the Research stop-policy intercepted the park transition. Its original records remain intact; any terminal disposition must use existing owner-authorized controls.
- Existing Fact Check, Synthesis, live steering, durable handoff, and prior Alpha findings remain the previously verified results. No `BUSINESS_PLAN` execution occurred.
