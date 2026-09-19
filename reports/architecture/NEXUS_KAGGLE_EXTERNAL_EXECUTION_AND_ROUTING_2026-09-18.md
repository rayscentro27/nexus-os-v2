# Nexus Kaggle External Execution and Routing

Status: `PARTIAL_BLOCKED_EXTERNAL`

This certification continued from the existing provider-neutral temporary
worker framework and Resource Governor. No second worker system, scheduler,
credential store, or control plane was created.

## Audit and current truth

| Component | Current state |
|---|---|
| Kaggle adapter | `PASS_REAL_BOUNDED` as a provider-interface adapter; blocked execution path is explicit |
| Kaggle auth | `NOT_PRESENT` |
| Kaggle CLI | Not installed (`command -v kaggle` returned no path) |
| Kaggle config | `~/.kaggle/kaggle.json` and `~/.config/kaggle/kaggle.json` absent |
| Kaggle Keychain | No matching `kaggle` or `nexus/credential.kaggle` item found |
| Kaggle launch | `BLOCKED_EXTERNAL`; no authorized notebook/kernel transport available |
| Artifact return | Adapter contract exists; no remote artifact can be returned without auth/transport |
| Cleanup | Blocked path is exception-safe and returns a bounded result; no remote session was created |
| Quota | `quota_known=NO`; never treated as unlimited |
| Duplicate Kaggle systems | None found |

The exact human boundary is: authorize a Kaggle account through the approved
credential path, install or expose the approved Kaggle CLI/API transport, and
approve a bounded CPU smoke notebook/job. No token was requested, printed,
created, or written.

The adapter now recognizes all current non-secret credential locations without
reading their values: `KAGGLE_API_TOKEN`, `~/.kaggle/access_token`, legacy
`KAGGLE_USERNAME` + `KAGGLE_KEY`, and legacy `~/.kaggle/kaggle.json`. A model
token/password is supported only when it is actually the account API token
accepted by those locations. A model-serving credential that authorizes only
model download/inference is not sufficient for notebook/kernel submission.
Kernel read access is distinct from kernel write/execute authorization; a
future submit/run canary requires account API/OAuth permission equivalent to
Kaggle's `kernels.editor` capability.

## Existing contracts reused

The existing `temporary_worker_framework.py` remains canonical for
`WorkerJob`, `WorkerResult`, `EnvironmentManifest`, provider probing, artifact
hash fields, cleanup state, and the Mac/Kaggle provider registry. The existing
`resource_governor.py` remains canonical for eligibility, explainable ranking,
production-readiness gates, fallback evaluation, and shadow-mode decisions.

The Governor remains:

* `RESOURCE_GOVERNOR_MODE=SHADOW`
* `AUTONOMOUS_ROUTING_ENABLED=NO`
* `AUTO_SPEND_ALLOWED=NO`

## Real machine-verifiable evidence

The real Kaggle provider probe returned:

```text
available=false
configured=false
cli_present=false
authorization_state=REAUTH_REQUIRED
gpu=UNKNOWN
artifact_download=false
quota_known=false
```

The existing real local fallback canary ran through the generic worker
framework and returned `SUCCEEDED` with two SHA-256-verified artifacts and
cleanup success. The Governor selected Mac for a free CPU smoke job. A GPU
job without production readiness received no selected provider and remained
in shadow evaluation.

These are not substitutes for a real Kaggle canary; they prove that the
Kaggle blocker is isolated and that Nexus has a working safe fallback path.

## Required external canaries after authorization

### Infrastructure canary

`SMOKE_TEST_V1` must be launched remotely with a deterministic job identity,
`result.json`, `artifact.txt`, timestamps, resource metadata, artifact
download, SHA-256 verification, canonical receipt, and remote cleanup.

### Productive canary

Use the existing restaurant production fixture only after its
`ProductionReadiness=READY` gate. The smallest useful workload is one bounded
internal creative artifact; no customer data, credentials, publication, or
large model download may be included. The expected chain is:

`CreativePackage → ProductionReadiness → WorkerJob → Governor → Kaggle →
WorkerResult → artifact hash → governed ingest → Creative QA input`.

Until authorization exists, `PRODUCTIVE_EXECUTION=BLOCKED_EXTERNAL`, not
`PASS_REAL`.

## Failure, fallback, and data boundaries

Kaggle failure, timeout, unknown quota, or missing authorization remains local
to the job. It cannot stop Hermes, Research, Alpha, the continuous runtime, or
other providers. The bounded fallback is Mac for safe CPU work, otherwise a
durable blocked/deferred job with no endless retries.

Kaggle may not receive client PII, credit reports, bank statements, Google or
Telegram credentials, payment secrets, or private internal credentials. The
planned smoke/productive canaries use no sensitive data. Unknown monetary cost
is not treated as free.

## CRJ research parallelism

The existing restart-safe Research queue accepted the bounded objective
`crj-goclear-capability-research-v1` with status `QUEUED`. It is independent of
Kaggle and does not block this certification. Research/Alpha own its later
execution and evidence review; this task did not invent a second queue.

## Nova/CEO visibility

Existing provider registry and Governor read models expose provider state,
authorization, capability, quota-known state, eligibility, ranking, and
whether execution occurred. The eventual external receipt must add provider
job ID, manifest, timings, artifact refs/hashes, resource usage, cleanup, and
next action. No secret is exposed.

## Decision

`AUTONOMOUS_ROUTING_DECISION=NOT_ACTIVATED`

Evidence is insufficient for bounded autonomous Kaggle routing because the
provider is unauthenticated and no supported launch transport exists in this
runtime. Resource Governor remains in `SHADOW`; Mac remains the safe local
path. This is a precise external blocker, not a Nexus-wide stop.

No publication, customer contact, spend, trade, credential creation, or media
generation occurred.

## Continuation certification

The existing Keychain item `nexus.kaggle.api_token` / account
`KAGGLE_API_TOKEN` was recovered into the current subprocess environment
without printing its value. The official Kaggle CLI `2.2.4` was installed in
an isolated `/tmp` target because Homebrew Python is externally managed; no
package or secret was added to the repository.

Authenticated read-only evidence passed:

* `kaggle datasets list --search nexus --page-size 1` returned public results;
* `kaggle kernels list --mine --page-size 1` returned the authorized account's
  existing kernel;
* `kaggle quota` returned GPU `0.00h used / 30.00h remaining` and TPU
  `0.00h used / 20.00h remaining`, refreshing at `2026-09-26T00:00:00`.

### Real smoke canary

`SMOKE_TEST_V1` executed as a private Kaggle kernel through the adapter:

* WorkerJob: `kaggle-smoke-1789780653`
* Provider job: `rayscentro/nexus-smoke-test-v1-25a50c88f0dd`
* Status: `SUCCEEDED`
* Runtime: approximately `19.82s`
* `result.json`: SHA-256 `ed809762ad86efc997503969a61cbccd53e422e2d1c1efa57877bcf72a6f1707`
* `artifact.txt`: SHA-256 `af26a6b7c78cc036eb9b72530be98c126ebd57ce7063942479b415313cc8c14d`
* Canonical destination: `data/governed/worker_artifacts/kaggle-smoke-1789780653`
* Remote deletion: successful

### Real productive creative canary

The existing GoClear restaurant production context was used without customer
data:

`creative_package_1c3c9494 → readiness_71528a69 → WorkerJob
CREATIVE_IMAGE_CANDIDATE → Kaggle → WorkerResult → governed artifact directory`

* WorkerJob: `kaggle-creative-1789780611`
* Provider job: `rayscentro/nexus-creative-image-candida-9b5c311e0e4b`
* Status: `SUCCEEDED`
* Runtime: approximately `26.88s`
* `creative_candidate.svg`: SHA-256 `4af509480aec86756e001ea531bb5caae1d0e0ae91ade03bbafd624021bb4b4d`
* `result.json`: SHA-256 `3b4f0943eead652e6cd1a668e8501c16cd705a6975b9de0599933b7e7c360c4d`
* Canonical destination: `data/governed/worker_artifacts/kaggle-creative-1789780611`
* Remote deletion: successful

The SVG is an internal, deterministic creative candidate carrying the approved
readiness transformation and an explicit no-guarantee constraint. It was not
published and was not sent to customers.

### Failure isolation

`FAILURE_TEST_V1` executed remotely and raised the intentional bounded failure:

* WorkerJob: `kaggle-failure-1789780690`
* Status: `FAILED`
* Failure receipt persisted
* Remote cleanup: successful
* Hermes/Research/continuous runtime: unaffected

Timeout behavior remains bounded by the adapter's execution deadline and CLI
timeouts; no separate expensive timeout run was needed after the real failure
path proved receipt and cleanup isolation.

### Governor update

The authenticated probe now feeds `FREE_QUOTA`, quota totals/remaining, and
provider health into the existing registry. The Governor remains
`SHADOW`/non-executing. It may identify Kaggle as the lowest-cost candidate for
a GPU-ready job only when GPU capability is verified; `UNKNOWN` GPU is now
explicitly ineligible and never treated as available.

### Research continuity

`crj-goclear-capability-research-v1` was not lost. The existing Research queue
claimed it and settled it as `FAILED_RETRYABLE` because the generic objective
processor received no source URL (`unknown url type: ''`). This is an isolated
Research retry issue, not a Kaggle blocker; no replacement queue or manual
Codex research was created.
