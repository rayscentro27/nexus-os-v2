# Nexus Criterion Tool Binding R5

## Result

`NEXUS_CLOSURE_EVIDENCE_CONVERGENCE_R4_REPORT.md` identified that Modal
criteria were being repaired with descriptive artifacts. R5 bound the failed
criteria to the existing `ModalRemoteWorkerProvider` and exercised the
health path. The first existing failed criterion now has real convergence.

## Existing canary state

Goal: `systems.modal_verification`  
Closure session: `closure_d55547e5aec91e3a7184`  
Criteria before this run: health check proven; bounded job result returned;
cost and authority boundaries recorded.

The session now records:

- `criteria_fixed`: `health check proven`
- `criteria_remaining`: `Bounded job result returned`, `Cost and authority boundaries recorded`
- `closure_state`: `FINALIZATION_RETRY`
- `next_action`: `FINALIZATION_RETRY`

## Capability binding

`resolve_criterion_capability()` is deterministic and criterion-specific:

| Criterion | Capability/tool | Action | Evidence type |
|---|---|---|---|
| health check proven | `modal.runtime` / existing `ModalRemoteWorkerProvider` | `modal.health_probe` | `LIVE_SERVICE_HEALTH` |
| bounded job result returned | `modal.bounded_job` / existing bounded worker | `modal.bounded_job` | `BOUNDED_EXECUTION_RECEIPT` |
| cost and authority boundaries recorded | `modal.governance` / provider controls and receipt | `modal.inspect_execution_controls` | `AUTHORITY_COST_RECEIPT` |

For Modal evidence criteria, the normal repair contract no longer selects
`internal.create_bounded_work_artifact`.

## Real runtime evidence

### AI-backed health repair

- AI receipt: `reports/runtime/ai_workforce_receipts/aiwf_3ab044fcb6774d96abc4957c21773d08.json`
- Worker: `nexus_ai_workforce`
- Model: `openai/gpt-4o-mini`
- Bound action: `modal.health_probe`
- Tool: `ModalRemoteWorkerProvider`
- Tool receipt: `reports/runtime/criterion_tool_receipts/modal_tool_9044d991516a499eb5fb394d231d21f2.json`
- Modal worker: `modal-worker-5c8902b8ebd2`
- Modal result: `HEALTHY`
- Active jobs: `0`; completed jobs: `0`; failed jobs: `0`
- Safety evidence: arbitrary shell, Stripe, and funded trading are
  `UNAVAILABLE`; the worker is optional and not a core health dependency.
- Acceptance test: `health probe returns a real bounded Modal status`
- Acceptance result: `VERIFIED`
- External side effects: `false`

The same existing executor was also exercised once directly before the
AI-backed run, producing tool receipt
`modal_tool_1ca544bbc49e46ca9c23d5c31cf11baf.json`; it is retained as
corroborating runtime evidence, not as a fabricated fixture.

## Exact remaining blocker

The repository contains the Modal adapter, `.venv-agent-platform` contains
Modal SDK 1.5.4, the `goclearonline` profile is authenticated, and the
health function is reachable. The bounded job path additionally requires
`NEXUS_REMOTE_WORKER_SHARED_SECRET` to sign the governed job. That secret is
not present in the current operator environment. No bounded Modal job was
claimed or attempted without it. This is a credential/authorization boundary,
not a reason to substitute a report artifact.

The cost/authority criterion can be inspected from an actual job receipt only
after a bounded job exists; it therefore remains pending honestly.

## Closure behavior

The resolver is used when building repair contracts and when deriving the
next work action. Modal health repair resolves to `modal.health_probe`; the
runner invokes the existing provider in the dedicated Modal environment and
writes the execution receipt. `record_criterion_verification()` attaches the
receipt, removes only the verified criterion, and persists `FINALIZATION_RETRY`
for the same closure session. The retry state survives reload. No generic
artifact was used as the health-tool evidence.

The normal operator cycles observed during this run selected Portal before
reaching the Modal session, so a scheduler-selected Modal retry was not
claimed. The criterion-specific AI/executor path itself was exercised with the
same governed runner action and real model/provider path.

## Tests

- Python compilation: passed.
- Focused goal-completion and Modal-provider tests: `24 passed`.
- Added coverage for deterministic Modal binding and prevention of generic
  artifact fallback.

## Final contract

```text
NEXUS_CLOSURE_EVIDENCE_CONVERGENCE_R5=PARTIAL
CRITERION_CAPABILITY_RESOLVER=PASS_REAL
GENERIC_ARTIFACT_NOT_USED_AS_TOOL_SUBSTITUTE=YES
EXISTING_MODAL_PATH_RECOVERED=YES
REAL_MODAL_TOOL_INVOCATION=PASS_REAL
REAL_MODAL_HEALTH_EVIDENCE=PASS_REAL
REAL_BOUNDED_MODAL_JOB=PARTIAL
REAL_EXECUTION_RECEIPT=PASS_REAL
CRITERION_ACCEPTANCE_TEST_AFTER_TOOL=PASS_REAL
FAILED_CRITERION_BECAME_VERIFIED=YES
REAL_CRITERION_CONVERGENCE=YES
AUTOMATIC_CLOSURE_CONTINUATION_AFTER_VERIFICATION=PARTIAL
REAL_GOAL_CONVERGENCE_PROVEN=NO
NEW_REAL_GOAL_TERMINAL_TRANSITION=NO
STALLED_SESSION_HANDLING=PASS
UNRELATED_PORTFOLIO_CONTINUES=PASS_REAL
CURRENT_RESEARCH_EXECUTION_MODE=REAL
NORMAL_CANONICAL_SUPERVISOR_ACTIVE=YES
NOVA_PROACTIVE_COMMUNICATION=ACTIVE
TRUE_RAY_BLOCKERS=NEXUS_REMOTE_WORKER_SHARED_SECRET is unavailable to the governed runner for signed bounded Modal jobs
SYSTEMATIC_OUTCOME_AUTONOMY=NO
```

The remaining work is to make the existing authorized signing secret
available through the established credential-control path, then let the same
resolver invoke and verify the bounded job. No model change, authority
expansion, or architecture rebuild is required.
