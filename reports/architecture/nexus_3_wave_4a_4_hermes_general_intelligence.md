# Nexus OS 3.0 Wave 4A.4 Hermes General Intelligence

Generated: 2026-07-20

## Starting Checkpoint

- Repository: `rayscentro27/nexus-os-v2`
- Branch: `main`
- Starting HEAD: `cd9fc5a6147074348f0fcdcaeea8862595699721`
- Starting commit message: `document hermes advisory context production certification`
- Starting dirty count: 142 paths before Wave 4A.4 edits.

## General-Intelligence Audit

Canonical Workroom messages enter `src/components/HermesChatPanel.jsx` and call `runHermesConversation` in `src/lib/hermes/hermesConversationEngine.ts`. The old `hermesResponseRouter.ts`, `hermesBrainPipeline.ts`, and priority router remain compatibility sources for older surfaces and tests.

## Generic-Fallback Root Cause

`src/lib/hermes/hermesResponseStrategy.ts` routed broad `FACTUAL_QUESTION`, `EXPLANATION`, `IDEA_REVIEW`, and `DECISION_SUPPORT` messages to one hard-coded response:

`My read: answer the immediate question first...`

That meant normal questions that did not match narrow executive intents could not reach time, report, customer, provenance, topic-continuation, or design evidence.

## Hybrid and Tool Registry

Wave 4A.4 adds `src/lib/hermes/hermesGeneralTools.ts` with a single registered Hermes tool catalog mapped to Capability OS. Unknown tools are rejected. Tool execution passes deterministic Capability OS policy before returning a read-only result.

Implemented tools:

- `hermes.current_time`
- `hermes.project_status`
- `hermes.list_reports`
- `hermes.read_report_summary`
- `hermes.find_report`
- `hermes.customer_aggregate`
- `hermes.system_health`
- `hermes.approval_summary`
- `hermes.work_summary`
- `hermes.revenue_summary`
- `hermes.capability_status`
- `hermes.explain_source`

## Provider Audit

Existing code references OpenRouter via Supabase `hermes-chat`, plus Gemini/Ollama support in the edge-function/provider layer and Groq/OpenRouter/Ollama in Alpha provider surfaces. Evidence is conflicting: older watch reports list missing Hermes model variables; later reports claim OpenRouter smoke success. Wave 4A.4 did not activate or rely on a paid/external model route.

Provider state for this wave: `TEST_ONLY` / evidence-conflicted, not used for certification.

## Conversation Coverage

The classifier now handles broad categories:

- current time/date;
- project and roadmap status;
- report catalog and lookup;
- customer aggregate status;
- previous-answer provenance;
- active readiness-review continuation;
- project discussion/design mode;
- misspellings such as `readines reviw`, `deparment`, and `systm`.

## Provenance

Every canonical response now receives bounded `HermesAnswerProvenance`. The session stores only tool IDs, evidence IDs, source labels, evidence state, generated timestamp, confidence, and answer kind. No chain-of-thought, secrets, or client PII are stored.

## Action Separation

Planning/design language stays conversational. Explicit task/review phrases create conversation-only governed task or Ray Review draft actions. Nothing is saved, assigned, charged, sent, deployed, or executed by this chat route.

## Framework Evaluation

See `reports/research/nexus_3_hermes_agent_framework_decision.md`. Decision: Nexus-native tool orchestration is sufficient for this wave; study LangGraph/Letta patterns only; defer memory frameworks until a durable-memory need is proven.

## Certification

Local focused certification:

- TypeScript: PASS
- Focused Hermes certification: PASS, 4 files / 33 tests
- Full unit suite: PASS, 95 files / 1481 tests, using an extended timeout for the existing recursive secret-scan test.
- Production build: PASS, with the existing Vite chunk-size warning.
- RLS authenticated persona harness: PASS, 45/45.
- Direct production RLS policy verifier: FAIL, 23 unsafe public or unconditional policy findings reported by `scripts/supabase/verify_production_rls_cli.py`.
- Local Playwright: BLOCKED before browser execution because `@playwright/test` is not installed in this checkout.
- Corpus: 200+ cases
- Holdout: 40 cases
- Generic fallback rate for supported safe cases: 0 in focused tests
- Action separation: 100% in focused tests
- Status/security honesty: 100% in focused tests

Live production certification was not rerun in this turn and remains pending for the new commit. Deployment was not performed because the strict production RLS verifier and browser certification gates are not clean.

## Security

Preserved:

- Capability OS preflight;
- Brain/Profile separation;
- Alpha no-Supabase boundary;
- Client aggregate-only customer answers;
- Stripe test-only / live deferral;
- live-trading block;
- no external framework installation;
- no arbitrary filesystem report scan.

## Department Operations Readiness

Department Operations remains `NEXT/PARTIAL`. It should not be approved until the new commit is deployed and the live authenticated Workroom sequence passes with zero page/console errors.
