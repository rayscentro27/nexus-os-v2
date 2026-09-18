# Nexus Model Benchmark and Tier Certification

Audit date: 2026-09-18 (America/Phoenix)

Scope: bounded model certification only. No Resource Governor routing, Nova
production model, provider configuration, Research routing, Alpha routing, or
coding executor was changed.

## Result

`MODEL_BENCHMARK_STATUS=PASS_REAL_WITH_LIMITS`

The benchmark produced useful task-specific evidence across six currently listed
OpenRouter models. It does not establish one universal winner. The strongest
free candidate in this run was `nex-agi/nex-n2.5-pro:free`; the current
`openai/gpt-4o-mini` remains a viable Tier 2 baseline; `google/gemini-2.5-flash`
was the best normal-cost broad candidate in this fixture; and
`google/gemini-2.5-pro` is a Tier 3 reasoning candidate when run with bounded
low reasoning and sufficient output budget. No Nous/Hermes free model was
callable or identified in the current catalog.

Certification is limited by synthetic bounded fixtures, small sample sizes, and
provider behavior that can change. Free models were repeated on C/D/E/H. All
critical role claims below identify those limits.

## Candidate inventory

| Model | Provider | Input / output price per M | Context | Tools | Vision | Free/paid |
|---|---|---:|---:|---|---|---|
| `openai/gpt-4o-mini` | OpenRouter → OpenAI | $0.15 / $0.60 | 128k | catalog YES | YES | Paid, very cheap |
| `inclusionai/ling-3.0-flash-vl:free` | OpenRouter | $0 / $0 | 262k | listed | image/video | Free |
| `nex-agi/nex-n2.5-pro:free` | OpenRouter | $0 / $0 | 262k | listed + structured | image | Free |
| `qwen/qwen3.8-27b:free` | OpenRouter | $0 / $0 | 262k | listed + structured | image/video | Free |
| `google/gemini-2.5-flash` | OpenRouter → Google | $0.30 / $2.50 | 1,048k | listed + structured | image/file/audio/video | Paid, normal |
| `google/gemini-2.5-pro` | OpenRouter → Google | $1.25 / $10 baseline | 1,048k | listed + structured | image/file/audio/video | Paid, premium |

Prices and model metadata were queried from the live OpenRouter catalog on the
audit date: [catalog](https://openrouter.ai/api/v1/models) and
[model guide](https://openrouter.ai/docs/overview/models).

Historical Nous/Hermes names were not included as a currently callable
OpenRouter candidate. Hermes Agent remains an executor/runtime distinction, not
proof that a free Nous/Hermes model is available.

## Benchmark method

All models received the same bounded system instruction and A–H fixtures:

- A: five-fact extraction from a fixed research artifact.
- B: four-part research summary preserving finding, evidence, uncertainty, next step.
- C: unavailable-tool and Gmail capability truth.
- D: bounded Nexus context plus immediate follow-up referent.
- E: challenge of weak evidence, assumption, contradiction, valid insight, next research.
- F: small Python defect requiring `price * quantity` for active items.
- G: current governed state versus older and stale conflicting documents.
- H: exact JSON object `{status, count}`.

The first pass used 48 task rows plus 24 critical repeat rows; D follow-up
exercises used a second HTTP turn. Gemini Pro and Qwen received a fairer
follow-up run after the first pass exposed configuration/provider behavior. Total
benchmark/diagnostic HTTP calls: 96. Results were captured under `/tmp` only;
no benchmark response or credential was committed.

Scoring is fixture-based, not subjective. A task passes only when the expected
facts/behavior and format are present. A model can be useful without receiving a
role certification if the sample or repeatability is insufficient.

## Raw scorecard

`PASS` means the bounded fixture passed. Latency is median of successful calls
where meaningful; costs are provider-reported usage costs for the calls shown.

| Model | A | B | C | D | E | F | G | H | Success / calls | Median latency | Cost observed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| gpt-4o-mini | FAIL | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | 8/8 | 2.24s | $0.000453 |
| Ling Flash VL free | PASS | PASS | 3/3 | 1/3 | 0/3 | PASS | FAIL | 1/3 | 13/16 | 0 |
| Nex N2.5 Pro free | PASS | PASS | 3/3 | 3/3 | 2/3 | PASS | PASS | 3/3 | 16/16 | 3.59s |
| Qwen 3.8 27B free | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | 0/16 | upstream 429 |
| Gemini 2.5 Flash | PASS | PASS | PASS* | PASS | PASS | PASS | FAIL | PASS | 8/8 | 0.81s | $0.001192 |
| Gemini 2.5 Pro, low reasoning | PASS | PASS | PASS* | PASS | PASS | PASS | PASS | format FAIL* | 8/8 | 2.86s | $0.013068 |

`*` Gemini capability/tool truth was semantically correct, but its C response
was not strict JSON in the first harness; Pro H used a JSON code fence and thus
failed strict parser validation. Both are repairable format issues, not provider
transport failures.

The initial Qwen failure was not an invented quality judgment. OpenRouter returned
HTTP 429 with `upstream_provider_shared_pool`; a later minimal probe returned
HTTP 200, `PROVIDER_TEST_OK`, and zero cost. This makes Qwen
`CALLABLE_INTERMITTENT`, not production-certifiable free routing.

### Repeatability detail

| Model | C repeats | D repeats | E repeats | H repeats | Consistency |
|---|---:|---:|---:|---:|---|
| Ling Flash VL free | 3/3 | 1/3 | 0/3 | 1/3 | inconsistent on context/challenge/JSON |
| Nex N2.5 Pro free | 3/3 | 3/3 | 2/3 | 3/3 | strongest free consistency in this run |
| Qwen 3.8 27B free | 0/3* | 0/3* | 0/3* | 0/3* | upstream rate-limit dominated |

`*` Qwen repeat calls were rejected with the same upstream 429. The separate
minimal success probe does not erase the operational reliability failure.

## Task observations

### A — extraction

Ling, Nex, Gemini Flash, and Gemini Pro passed the exact five-fact fixture.
GPT-4o-mini missed at least one expected fact under this prompt. This is a
bounded extraction result, not evidence that GPT-4o-mini cannot extract generally.

### B — summary

All models that returned usable output preserved the requested four-part shape.
Free candidates sometimes used more output than necessary; Flash was concise.

### C — tool truth

Nex and Ling repeated the unavailable-tool behavior correctly. GPT-4o-mini failed
the strict fixture in this run, despite the already-proven production capability
truth layer around Admin Nova. Gemini models expressed the correct inability but
needed output-format hardening. No candidate was allowed to claim Gmail access.

### D — Nova context and referent

Nex passed all three repeat runs; the baseline and Flash passed their bounded
turns; Ling varied. Nex is the strongest candidate for a free grounded context
lane from this sample.

### E — Alpha challenge

Gemini Flash, GPT-4o-mini, and Gemini Pro identified the core defects. Nex passed
two of three repeats. Ling failed all three repeat attempts under the rubric.
This is the main reason Ling is not recommended for Alpha review.

### F — coding

Usable candidates returned the required `price * quantity` repair. This fixture is
too small to replace Codex CLI or certify a coding executor/model workflow.

### G — precedence

Nex and GPT-4o-mini selected current governed state. Ling failed. Flash failed
the precedence fixture. Pro passed after low-reasoning configuration.

### H — structured output

Nex passed all three repeats. GPT-4o-mini, Ling, and Flash passed their single
base runs, but Ling was inconsistent in repeats. Pro produced valid JSON inside a
markdown fence, which is a strict-schema failure until a parser retry/format
constraint is applied.

## Free model failure modes

### `nex-agi/nex-n2.5-pro:free`

Best free result: 16/16 HTTP-successful benchmark rows, C/D/H repeated 3/3,
E repeated 2/3. Latency was materially slower than Flash and had a high p95 in
the repeated sample. Recommended only for bounded low-cost work with timeouts,
one retry, and fallback to the current paid baseline.

### `inclusionai/ling-3.0-flash-vl:free`

Fast enough and good at extraction/tool honesty, but failed repeatable Alpha
challenge, stale-source precedence, and strict JSON consistency. Not suitable for
Nexus-grounded executive or review work without a stronger verifier.

### `qwen/qwen3.8-27b:free`

Catalog-listed and minimally callable, but batch and repeat calls were dominated
by upstream shared-pool HTTP 429s. Not suitable for a dependable Tier 1 route
until provider routing or a dedicated key/path is proven.

### Nous/Hermes

`NOUS_HERMES_CALLABLE=NO`

`NOUS_HERMES_STATUS=UNPROVEN_EXTERNAL_ACCESS`

No current candidate, authenticated free endpoint, or repeatable inference path
was established. No quality or role claim is made.

## Role certification

These are bounded certifications, not production activation decisions.

| Role | Certified model | Alternate | Failed/limited candidates |
|---|---|---|---|
| TIER1_EXTRACTION | Nex N2.5 Pro free | Gemini Flash | GPT baseline missed fixture fact |
| TIER1_CLASSIFICATION | Nex N2.5 Pro free | gpt-4o-mini | Needs broader labeled set |
| TIER1_SUMMARIZATION | Nex N2.5 Pro free | Gemini Flash | No major failure in fixture |
| TIER1_STRUCTURED_OUTPUT | Nex N2.5 Pro free | gpt-4o-mini / Flash | Ling inconsistent; Pro fence output |
| TIER2_NOVA_CHAT | gpt-4o-mini | Gemini Flash | Free models need latency/reliability guardrails |
| TIER2_TOOL_ROUTING | Nex N2.5 Pro free (model-only fixture) | Gemini Flash | Admin tools remain unavailable; no direct tool execution certified |
| TIER2_RESEARCH_SYNTHESIS | Gemini Flash | gpt-4o-mini | Flash missed one precedence fixture |
| TIER2_ALPHA_REVIEW | Gemini Flash | Gemini Pro | Ling failed repeats; Nex had one miss |
| TIER2_LONG_CONTEXT | Gemini Flash candidate | Gemini Pro | This fixture was short; true long-context still needs larger test |
| TIER3_REASONING_ESCALATION | Gemini Pro with low reasoning | Gemini Flash | Pro needs format guard/adequate token budget |
| TIER3_HIGH_VALUE_STRATEGY | Gemini Pro candidate, not activated | Gemini Flash | Requires business-quality evaluation |
| CODING_SUPPORT | No new model certification | Codex CLI remains current executor | Small F fixture is insufficient for replacement |

## Proposed tiers from evidence

### TIER_0

- Tasks: deterministic classification, retrieval, schema checks, FFmpeg, local
  Whisper when health is proven.
- Escalation: ambiguity, missing evidence, failed deterministic validation.
- Max retries: 0–1.
- Cost: local/near-zero.

### TIER_1

- Model: `nex-agi/nex-n2.5-pro:free` for extraction, summaries, classification,
  and structured output.
- Escalate on provider 429, latency budget breach, E failure, or any tool-truth
  mismatch.
- Max retries: one; then gpt-4o-mini fallback.
- Cost: provider-listed free, but retry/latency cost is operationally real.

### TIER_2

- Models: current `openai/gpt-4o-mini` for Nova chat; Gemini Flash for research
  synthesis and Alpha review.
- Escalate on low confidence, source conflict, high business value, long context,
  or repeated schema/tool failure.
- Max retries: one bounded retry, then Tier 3 only if trigger is present.
- Cost: gpt-4o-mini is sub-cent for short turns; Flash is materially more costly
  but still low absolute cost for bounded context.

### TIER_3

- Model: Gemini Pro with `reasoning.effort=low` or an approved equivalent;
  reserve for high-value/difficult reasoning and multimodal work.
- Escalate on high cost of error, unresolved contradiction, long-context source
  precedence, or repeated Tier 2 failure.
- Max retries: one format/transport retry; no unbounded premium loops.
- Cost: roughly milliper-call for short inputs in this run, rising quickly with
  output/reasoning and long context.

## Measurable escalation signals

Escalate when any of the following occurs:

1. `LOW_CONFIDENCE`: required evidence field absent or answer hedges where source
   is present.
2. `TOOL_TRUTH_FAILURE`: model claims an unavailable tool or invents a result.
3. `SCHEMA_FAILURE`: invalid JSON after one bounded repair attempt.
4. `CONTRADICTION_DETECTED`: selected facts conflict across source planes.
5. `HIGH_BUSINESS_VALUE`: decision, client, financial, or production-impacting work.
6. `HIGH_COST_OF_ERROR`: privacy, compliance, money, or external publication.
7. `LONG_CONTEXT_COMPLEXITY`: context exceeds the validated lower-tier window or
   contains competing current/historical records.
8. `REPEATED_RETRY`: provider errors, 429s, timeout, or repeat variance.
9. `PREMIUM_REQUIRED`: lower tier fails the same labeled task twice or cannot
   satisfy required reasoning/vision constraints.

## Cost comparison

The following is a transparent short-context scenario using observed fixture
costs, not a monthly invoice. It includes 100 extraction tasks, 100 summaries,
100 Alpha reviews, 100 Nova conversations, and 20 escalations.

| Strategy | Routing assumption | Estimated total |
|---|---|---:|
| All gpt-4o-mini | All 420 tasks use baseline; observed A/B/E/D costs | **~$0.030** |
| Tiered routing | Nex free for A/B; gpt-4o-mini for D; Flash for E; Pro low-reasoning for 20 escalations | **~$0.067** |
| Free-first | Nex free first; Flash fallback for E; gpt baseline for D fallback; Pro for 20 escalations | **~$0.061–$0.067** |

For these tiny prompts, all-gpt-4o-mini is cheaper than escalation-heavy routing.
Tiering becomes economically justified when free models materially reduce paid
volume, context sizes grow, or task quality/value—not merely because a model is
listed free. Provider failures and retries can erase nominal savings.

## Latency and reliability

| Model | Median observed | p95/upper observed | Provider failures |
|---|---:|---:|---|
| gpt-4o-mini | 2.24s | 3.38s | 0/8 |
| Ling free | 2.28s | 3.00s successful | 3/16 rows in repeat run |
| Nex free | 3.59s | ~12.34s in repeats | 0/16 |
| Qwen free | none in batch | 0 successful batch calls | 16/16 HTTP 429; later single probe 200 |
| Gemini Flash | 0.81s | 1.03s | 0/8 |
| Gemini Pro low reasoning | 2.86s | 3.53s | 0/8 |

The free-first strategy must include an availability circuit breaker. A free model
that repeatedly 429s is not a useful default regardless of nominal price.

## Unresolved gaps

- A–H fixtures are small and synthetic; no production traffic was modified.
- Coding certification needs a real patch/test fixture and executor-specific
  harness; this audit intentionally did not replace Codex CLI.
- Long-context certification needs multi-document payloads large enough to test
  retention and context-window behavior.
- Direct tool execution was not activated; model tool metadata is not proof of
  Admin MCP availability.
- Nous/Hermes free inference remains unproven.
- Free catalog routing, limits, and provider pools can change without notice.
- Production cost estimates need real Nexus token telemetry over a representative
  week.

## Final fields

`MODEL_BENCHMARK_STATUS=PASS_REAL_WITH_LIMITS`

`MODELS_TESTED=gpt-4o-mini; Ling 3.0 Flash VL free; Nex N2.5 Pro free; Qwen 3.8 27B free; Gemini 2.5 Flash; Gemini 2.5 Pro`

`NOUS_HERMES_STATUS=UNPROVEN_EXTERNAL_ACCESS`

`TIER1_CERTIFIED_MODELS=nex-agi/nex-n2.5-pro:free for bounded extraction,
summary, classification, structured output`

`TIER2_CERTIFIED_MODELS=openai/gpt-4o-mini for Nova chat; google/gemini-2.5-flash for bounded research/Alpha work`

`TIER3_CERTIFIED_MODELS=google/gemini-2.5-pro as a bounded reasoning candidate;
strict JSON requires format repair`

`NOVA_CHAT_CERTIFIED_MODEL=openai/gpt-4o-mini`

`TOOL_ROUTING_CERTIFIED_MODEL=nex-agi/nex-n2.5-pro:free for model-only truth fixture; Admin tool execution not certified`

`RESEARCH_EXTRACTION_CERTIFIED_MODEL=nex-agi/nex-n2.5-pro:free`

`RESEARCH_SYNTHESIS_CERTIFIED_MODEL=google/gemini-2.5-flash`

`ALPHA_REVIEW_CERTIFIED_MODEL=google/gemini-2.5-flash`

`LONG_CONTEXT_CERTIFIED_MODEL=none yet; Gemini Flash/Pro candidates only`

`STRUCTURED_OUTPUT_CERTIFIED_MODEL=nex-agi/nex-n2.5-pro:free`

`CODING_SUPPORT_CERTIFIED_MODEL=none new; Codex CLI remains current executor`

`FREE_MODEL_FAILURE_MODES=upstream 429; latency variance; inconsistent referent/precedence; malformed or fenced JSON; challenge weakness`

`CURRENT_ALL_GPT4O_MINI_COST_ESTIMATE=~$0.030 for stated short-task scenario`

`TIERED_ROUTING_COST_ESTIMATE=~$0.067 for stated short-task scenario`

`FREE_FIRST_COST_ESTIMATE=~$0.061–$0.067 including paid fallback/escalation`

`RESOURCE_GOVERNOR_IMPLEMENTATION_READY=YES, design only; do not activate from this report alone`

`REPORT_PATH=reports/architecture/NEXUS_MODEL_BENCHMARK_AND_TIER_CERTIFICATION_2026-09-18.md`

`FILES_CHANGED=this report only`

`TESTS_RUN=96 live OpenRouter benchmark/diagnostic HTTP calls; model catalog query; bounded A–H scoring; repeated C/D/E/H free-model tests`

`COMMITS=PENDING`

`RAY_ACTION_REQUIRED=NO`

`RAY_DECISION_REQUIRED=YES before activating any free model or Tier 3 route`

`NEXT_MACHINE_ACTION=expand the labeled benchmark with real long-context and
coding fixtures, then design—but do not yet activate—the Resource Governor`
