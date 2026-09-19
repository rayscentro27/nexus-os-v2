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
