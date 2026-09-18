# Nexus Intelligence Pipeline / Alpha Certification

Date: 2026-09-18 (Phoenix)

## Scope and boundary

This certification extends the existing Last30Days, Research V2, Alpha model
review, governed handoff, and result-feedback paths. It does not change the
Research scheduler, Hermes, Resource Governor, external integrations, or any
consequential action authority.

The resulting flow is:

`Last30Days acquisition -> source-role filtering -> semantic coherence judge ->
Research evidence/need -> model-backed Alpha -> governed department handoff ->
bounded internal work -> result feedback`

## Semantic demand preparation

`scripts/nexus_agent_platform/research/semantic_intelligence.py` now provides a
bounded reusable query-expansion contract, source-role metadata, negative
filtering, customer-language boundaries, demand/factual confidence separation,
and a model-backed coherence judge. Last30Days remains acquisition-only.

For the live business-credit test, focused acquisition used current Reddit
evidence from the pinned Last30Days runtime. The semantic judge used
`openai/gpt-4o-mini` with one OpenRouter call. It retained three signals about
new-business credit denial/qualification uncertainty, rejected four unrelated
signals, and extracted observed language including “denied business credit”,
“uncertain about eligibility”, “new business credit cards”, and “vendor
tradelines”.

Demand confidence is separate from factual confidence: the evidence supports
that people are discussing the problem, while lender thresholds and causal
claims still require verification. The existing need
`need_f527d1db8c4d1e5de721` was reused; no duplicate need was created.

## Alpha decision certification

The existing `alpha_model_review.py` path was reused. A small compatibility fix
now accepts `source_url`, `source_title`, and `excerpt` fields so Alpha receipts
retain actual source references. Existing need IDs are preserved during review
instead of creating duplicate needs.

### QUALIFY

- model/provider: OpenRouter / `google/gemini-2.5-flash`
- model calls: 1
- receipt: `alpha_receipt_4c6a63f9dbdf464c8512250f396037e3`
- decision: `QUALIFY`
- need: `need_f527d1db8c4d1e5de721`
- source references: 3
- handoff: `research_handoff_173c26c258a14528b440a29318c8ca76`

Alpha considered service, consulting, education, lead-generation, affiliate,
and referral paths. No external action was taken.

### RESEARCH_MORE

A deliberately insufficient single-signal package produced a real Gemini
review with decision `RESEARCH_MORE`. Alpha identified missing source
diversity, audience size, specific desired outcome, problem frequency/severity,
and existing-solution evidence. The existing queue path created an assigned
follow-up with priority 2:
`alpha-model-followup:alpha_eval_820c24e80bcd434aa85f171f60831e91`.

### REJECT

A GitHub repository/stars package with no customer problem, audience, demand,
or commercial evidence produced a real Gemini `REJECT`. No department handoff
was created.

## Routing and bounded department execution

Routing is based on explicit finding class/domain, not incidental words. The
certification exercised:

| Finding class | Department | Result |
|---|---|---|
| Funding/customer credit | CLYDE_CREDIT | accepted, bounded internal analysis completed |
| SEO/search opportunity | SEO | accepted, bounded internal opportunity brief completed |
| Capability/platform | SYSTEMS_ENGINEERING | accepted, bounded integration assessment completed |

Each produced a governed handoff, work item, and result-feedback receipt with
the Alpha receipt and finding IDs preserved. External mutation was false for
all three. No publication, customer contact, spend, trade, or production
mutation occurred.

Negative routing checks prevent a GitHub software artifact from routing to
Funding, a customer complaint mentioning software from routing automatically
to Systems, and a generic SEO technical warning from routing to Creative.

## Topicless discovery

The live two-stage proof used the query `small business customer problems
gaining momentum`. Stage 1 returned 9 signals across Reddit, Hacker News, and
GitHub, with 10 upstream discovery clusters. Stage 2 treats up to three
selected themes as investigation candidates requiring semantic coherence and
Alpha; it does not auto-promote them to opportunities.

## Operational visibility

`research_operational_state.py` now projects current Alpha decisions, handoffs,
and department result feedback from canonical governed stores. Nova can use the
existing operational path to distinguish Research findings, Alpha decisions,
department receipt/acceptance, completed bounded work, and feedback awaiting
Research/Alpha interpretation.

## Safety

External mutations: none. Customer contact: none. Publication: none. Trades:
none. Money spent: none. Resource Governor remains inactive. Scheduler and
Hermes architecture were unchanged.

## Remaining limitations

The semantic judge is evidence preparation, not factual verification or
business approval. HN/GitHub are intentionally low-weight for customer-pain
clusters. Topicless candidates remain candidates until focused evidence passes
the same semantic and Alpha gates. Department result feedback is persisted and
correlated; downstream teams still need their own richer specialist artifacts
when a real business objective requires them.
