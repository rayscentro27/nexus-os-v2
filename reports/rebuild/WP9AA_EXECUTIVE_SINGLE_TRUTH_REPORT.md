# WP9AA Executive Single-Truth Report

## Executive Result

The WP9Z human response exposed a composition defect: a correct verified
projection was appended beneath contradictory model prose. WP9AA repairs the
boundary so current-state answers are composed once from an authoritative
fact object. Hermes remains the reasoning engine upstream; final factual slots
cannot be contradicted by model prose.

## Response Assembly Trace

Before repair, `_process_message_inner` in
`scripts/nova/nova_telegram_worker.py` accepted the raw Oracle response via
`_response_integrity()` and then appended the grounding block. The integrity
function checked only empty/raw envelopes. This was the contradiction entry
point: `RAW_MODEL_CURRENT_FACTS_ACCEPTED=YES`.

After repair, current-state detection creates `verified_current_state` before
the Oracle model call, and the same object controls final composition. The
current-state path does not reuse free-form model prose, preventing unlabeled
contradictions as well as conflicting labeled fields.

## Authoritative Fact Contract

`scripts/nexus_agent_platform/grounded_response.py` owns a single bounded
projection for the request: health, Ray action classification, Finance,
Alpha, and runtime provenance. It reads existing artifacts and the runtime
envelope; it is not a new database or state store. Hermes still owns
interpretation and synthesis for ordinary conversation and non-current-state
requests.

## Response Semantics

The final composition states that Nexus is operational with telemetry
degraded, nothing currently requires Ray action, Finance and Alpha are
available, and the runtime is Oracle Hermes 0.20.6 / `nova_nexus` /
OpenRouter / `openai/gpt-4o-mini`. Unknown environment versions remain
explicitly unknown. Null active-service values are not converted to zero.

## Adversarial Contradiction Tests

The focused suite tests contradictory labeled claims and unlabeled model
narrative, including false Finance/Alpha availability, false runtime, false
health, and unsupported Python/OS/Podman versions. All are excluded from the
current-state answer or represented as unknown when evidence is absent.

## Fresh Non-Human Test

A fresh real Oracle request using the human-certification semantics completed
successfully through Hermes 0.20.6. All five completeness fields passed:
health, Ray priority, Finance, Alpha, and runtime. The resulting answer was a
single coherent composition with no contradictory model facts.

## Regression

Focused WP9Z/response tests: 10 passed. Python compilation passed. Existing
Oracle bridge, profile, MCP, Finance, Alpha, Telegram route, session, and
dedup evidence were not architecturally changed. No new Telegram ingress was
simulated and the WP9X event was not replayed.

## Human Handoff

`NEW_HUMAN_MESSAGE_REQUIRED=YES`.

Ray must send:

> Nexus, WP9Z human certification NEXUS-WP9Z-7F4A2C. Give me a concise executive briefing: current Nexus health, anything that truly requires my action now, verified Finance and Alpha availability, and the exact verified Hermes runtime answering me.

This message was not sent by Codex.

## Security and Git

No secrets were printed. WP9 scheduler and unrelated worktree changes were
preserved. WP9AA changes are the grounded response module integration,
focused tests, and this report.
