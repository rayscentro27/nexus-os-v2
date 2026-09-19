# NEXUS Research / Alpha Recovery and Controlled Reactivation Certification

Certification date: 2026-09-19. This is a before-reactivation certification; continuous Research was not resumed because the Hermes grounding gate failed.

REPAIR_STATUS=RESEARCH_REPAIRED_HERMES_GROUNDING_BLOCKED

SOURCE_PURPOSE_MODEL=Implemented in `scripts/nexus_agent_platform/research/source_semantics.py`: TEST_EXAMPLE, HISTORICAL_REFERENCE, INSTALLED_CAPABILITY, MONITOR_ONLY, ACTIVE_DISCOVERY, ACTIVE_INVESTIGATION, EXTERNAL_EVIDENCE_SOURCE.
LEGACY_TEST_SOURCE_STATUS=Phoenix mobile detailing, HubSpot affiliate, and Shopify Partners are classified TEST_EXAMPLE and excluded from autonomous discovery pools.
INSTALLED_CAPABILITY_STATUS=SEO Engine and Last30Days repositories are classified INSTALLED_CAPABILITY and removed from scheduler source lanes; adapters remain callable for maintenance/invocation.

## Capability certification

| CAPABILITY | AVAILABLE | INVOCATION_PATH | REAL_CANARY | RESULT |
|---|---|---|---|---|
| Last30Days | YES | `nexus_agent_platform.research.last30days_adapter.run_demand_radar` | `codex-cert-last30days-20260919` | PASS_REAL; live HN/Reddit run returned PASS; separate GitHub run returned 5 signals with `github=OK`. |
| SEO Engine | YES | `nexus_agent_platform.research.seo_adapter.adapter` | `codex-cert-seo-20260919` | PASS_REAL; SEO 0.2.40 crawled the live GoClear site, returned 14 findings, persisted 5. |
| Web/source acquisition | YES | Brave search plus `alpha.alpha_discovery.retrieve_page` | Fresh no-show objective | PASS_REAL; two live searches and four page retrievals succeeded. |
| Reddit/HN/GitHub acquisition | YES | Last30Days source adapters | Fresh demand/GitHub runs | PASS_REAL; Reddit/HN live run and GitHub live run completed. |
| YouTube pipeline | YES, bounded | `research.youtube_full_pipeline.process_youtube_video` | Fresh video `S7y7N9V2_b4` | PASS_REAL_BOUNDED; transcript/caption access failed truthfully, metadata fallback persisted `PARTIAL_EVIDENCE`. |
| Research document/source processors | YES | `research.scheduled_research_router.process_scheduled_item` | Fresh YouTube item | PASS_REAL; produced V2 package, claim, question, and evidence-incomplete state. |
| Alpha consumer | YES | `alpha_model_review.review_demand_package` | Fresh demand and YouTube packages | PASS_REAL; OpenRouter model calls completed with `RESEARCH_MORE` receipts and follow-up work. |
| Clyde/funding Research path | AVAILABLE | Existing governed funding/Clyde handoff path | Not run in this fresh demand objective | NOT_REQUIRED_FOR_CODEX_GATE; no external funding action performed. |

YOUTUBE_LAST_KNOWN_GOOD=Existing successful transcript artifacts under `reports/runtime/youtube_artifacts`; prior path acquired captions or local ASR and wrote transcript/summary/extraction/provenance.
YOUTUBE_FAILURE_ROOT_CAUSE=Fresh video had no public English caption track and yt-dlp media acquisition required sign-in; cookies/auth are intentionally disabled.
YOUTUBE_REGRESSION_FOUND=YES; the old failure branch discarded all evidence and marked the objective retryable without preserving metadata or continuing the investigation.
YOUTUBE_REPAIR=Persist truthful metadata/description as `PARTIAL_EVIDENCE` with `EVIDENCE_INCOMPLETE`, explicit fallback ladder, no fabricated transcript claims, V2 persistence, follow-up questions, and assigned Alpha review.
YOUTUBE_REAL_TEST=PASS_REAL_BOUNDED; `S7y7N9V2_b4` produced a durable partial-evidence artifact and V2 package.
YOUTUBE_FALLBACK_TEST=PASS_REAL; captions → local ASR → metadata/description fallback executed; transcript remained explicitly unavailable.
YOUTUBE_FALLBACK_LADDER=public captions → local ASR → metadata/description → independent text source.
YOUTUBE_FAILURE_DOES_NOT_STOP_OBJECTIVE=YES

PRE_PROCESS_DUPLICATE_CHECK=PASS_REAL; `codex-cert-duplicate-20260919` emitted `pre_process_duplicate_check` and made zero processor/network calls.
DUPLICATE_TEST=PASS_REAL; unchanged source was recognized before expensive processing and Alpha was skipped.

FAILURE_RECOVERY_REPAIR=Strategy-changing fallback queues the next source candidate and marks the objective WAITING rather than repeating the same failed method.
FAILURE_RECOVERY_TEST=PASS_REAL; bounded canary queued `alternate-source` with `strategy_change_after_SCHEDULED_PROCESSOR_FAILURE` and `objective_continues=true`.

AI_INVESTIGATION_OWNER=Research AI; scheduler only leases/rotates work.
FOLLOWUP_INVESTIGATION_TEST=PASS_REAL; fresh no-show objective executed a second search question and retrieved independent evidence.
CROSS_SOURCE_TEST=PASS_REAL; four current pages from distinct domains were retrieved and persisted.

CUSTOMER_DEMAND_TEST=PASS_REAL; fresh appointment no-show investigation preserved audience/problem/evidence gaps, customer-language snippets, alternatives, follow-up question, and Alpha status without requiring a business model first.

DURABLE_INFORMATION_GAIN=PASS_REAL; fresh demand sources, research package, claims/questions, partial YouTube evidence, Alpha evaluations, receipts, and follow-up work IDs persisted.
EVIDENCE_TO_ALPHA_HANDOFF=PASS_REAL; fresh demand and YouTube evidence packages reached the Alpha model bridge.
MODEL_BACKED_ALPHA=PASS_REAL; OpenRouter `openai/gpt-4o-mini`, one model call per tested package, real receipts persisted.

ALPHA_REJECTION_SEMANTICS=Repair complete; incomplete/unverified evidence maps to RESEARCH_MORE, contradictions preserve evidence and request resolution, and model prompts require secondary-value consideration before REJECT.
SECONDARY_VALUE_ROUTING=Model prompt evaluates service, affiliate, referral, lead generation, content, education, comparison, white-label, software, and no-opportunity paths; no unsupported rejection was manufactured in these tests.

## Codex real certification

CODEX_TEST_A=PASS_REAL — fresh appointment no-show demand; two searches, four retrieved sources, follow-up, durable package, model-backed Alpha RESEARCH_MORE.
CODEX_TEST_B=PASS_REAL — Last30Days invoked on a fresh no-show topic and returned live multi-source output.
CODEX_TEST_C=PASS_REAL — SEO Engine invoked against a live target and returned structured findings.
CODEX_TEST_D=PASS_REAL_BOUNDED — fresh YouTube selected; transcript limitation preserved; fallback evidence, follow-up, and Alpha RESEARCH_MORE receipt persisted.
CODEX_TEST_E=PASS_REAL — failure classified and alternate source queued without same-strategy retry.
CODEX_TEST_F=PASS_REAL — duplicate prefilter ran before expensive processing.
CODEX_TEST_G=PASS_REAL_BOUNDED — real model-backed Alpha produced RESEARCH_MORE; QUALIFY or REJECT was not fabricated where evidence did not warrant it.

BUSINESS_MODEL_BENCHMARK=PASS_REAL — live Brave research returned current evidence for all ten models: productized AI service, affiliate/referral, lead generation, digital products, education/coaching, creator/newsletter, paid membership, ecommerce, micro-SaaS, and marketplace/platform. Each row captured monetization, acquisition, automation fit, startup complexity, failure mode, and next investigation; no model was rejected solely for incomplete evidence.

| model | proven model / money path | acquisition / automation | common failure | next Research question |
|---|---|---|---|---|
| Productized AI service | recurring service/availability fees | outbound/content/referrals; high automation fit | commodity delivery and unclear offer | Which narrow segment pays for a measurable outcome? |
| Affiliate/referral | CPA, CPL, CPS, recurring commission | audience/SEO/partners; medium-high fit | commission does not cover acquisition cost | Which offer has verified fit and compliant economics? |
| Lead generation | pay-per-lead/appointment | search/outbound; high workflow fit | vague qualification and weak conversion | Which niche has verified lead value? |
| Digital products/tools | one-time or bundled digital sales | creators/affiliates; high fit | product built without demand | Which repeated need supports paid validation? |
| Education/coaching | cohort, subscription, coaching fees | authority/content; medium-high fit | weak outcome proof and churn | Which outcome can be evidenced before selling? |
| Creator/newsletter | sponsorships, affiliates, subscriptions | audience/content; high assist fit | audience/conversion dependency | Which audience and paid intent are observable? |
| Paid membership | recurring dues | community/content; medium fit | churn and low engagement | What retention behavior is measurable? |
| Ecommerce | product margin/repeat purchase | paid/search/creator; medium fit | CAC compresses margin | Can a differentiated niche clear unit economics? |
| Micro-SaaS | recurring subscription | niche distribution/integrations; high fit | churn, platform dependency, underpricing | What narrow workflow has paid demand? |
| Marketplace/platform | take rate/listing/transaction fees | supply-demand network; medium fit | liquidity and premature monetization | Can one side reach liquidity safely? |

PREMATURE_REJECTION_FOUND=NO
CODEX_RESEARCH_CERTIFICATION=PASS_REAL

## Hermes / Nova certification

HERMES_OBJECTIVE_CREATED=YES — Oracle delegation `nexus-delegation-b0846c8db74d47679e4c7f538d780e5e`.
HERMES_RESEARCH_STARTED=YES — Oracle Hermes 0.20.6, profile `nova_nexus`, toolset `nexus_mcp_remote` returned SUCCEEDED.
HERMES_TOOL_USE=FAIL_GROUNDED — Nova claimed live tool use but returned stale CRJ/affiliate/YouTube records and no exact fresh-objective URLs or matching local evidence receipt.
HERMES_FOLLOWUP=FAIL_MATCH — follow-up response remained stale and did not resolve the fresh objective against the local evidence package.
HERMES_ALPHA_REVIEW=FAIL_MATCH — remote response gave delegation/pending language, not the local model-backed Alpha receipt or exact decision.
HERMES_FINAL_REPORT=FAIL_GROUNDED — response was not canonical-evidence grounded.
NOVA_GROUNDING_MATCH=NO
HERMES_RESEARCH_CERTIFICATION=FAIL_REAL

CONTINUOUS_RESEARCH_REACTIVATED=NO — blocked by Hermes cross-runtime grounding gate; no continuous scheduler was started or duplicated.

UNIQUE_NEW_SOURCES=Fresh no-show sources persisted; legacy/test examples excluded.
DUPLICATES_SKIPPED_PREPROCESSING=1 certification canary.
SOURCE_FAILURES=YouTube transcript/media acquisition limitation observed; no fabricated content.
FAILURE_RECOVERIES=1 strategy-changing queue reroute proven; YouTube continued through metadata fallback.
FALLBACKS_USED=YouTube metadata/description fallback; source-candidate reroute.

RAW_CUSTOMER_SIGNALS=Current no-show complaints/solution signals from live web search and Reddit evidence.
NEW_CUSTOMER_NEEDS=1 fresh appointment no-show need cluster, status incomplete pending segment/economics validation.
NEW_INTELLIGENCE_ITEMS=1 durable fresh demand package plus 1 durable YouTube incomplete-evidence package.
FOLLOWUPS_COMPLETED=1 fresh demand cross-source follow-up; additional Alpha follow-up work queued.
ALPHA_REVIEWS=3 model-backed reviews across fresh demand and YouTube packages.
DEPARTMENT_HANDOFFS=0 — Alpha decisions were RESEARCH_MORE; no unsupported downstream handoff.

TRUE_INVESTIGATION_RATE=PASS_REAL for certification flows; live historical baseline remains 0%.
WASTED_CYCLE_RATE=Certification duplicate/failure lanes avoided expensive repeat processing; historical baseline remains 49.6%.

FILES_CHANGED=research source semantics, dispatcher prefilter/failure reroute, YouTube bounded fallback, Alpha incomplete-evidence semantics, certification report, and updated targeted test expectation.
TESTS_RUN=29 targeted Python tests; Python compile checks; Last30Days/SEO/web/GitHub/YouTube/Alpha real canaries; duplicate prefilter; failure reroute; Oracle Hermes 0.20.6/Nova calls; business-model benchmark.
TEST_RESULTS=Codex certification PASS_REAL. Hermes certification FAIL_REAL due remote stale-data/evidence-grounding mismatch.
COMMITS=5e2c0185 pushed to origin/main

RAY_ACTION_REQUIRED=YES — approve/repair the Oracle Hermes remote Research↔Alpha evidence bridge before reactivation.
TRUE_EXTERNAL_BLOCKERS=Remote `nexus-hermes-0206` is reachable and reports Hermes 0.20.6/profile nova_nexus, but its Research/MCP persistence is not grounded to the fresh objective or the local canonical evidence/Alpha ledger.
NEXT_MACHINE_ACTION=Repair remote Research objective persistence and evidence/Alpha receipt correlation; rerun Hermes Test, then reactivate the existing continuous owner only after HERMES_RESEARCH_CERTIFICATION=PASS_REAL.
