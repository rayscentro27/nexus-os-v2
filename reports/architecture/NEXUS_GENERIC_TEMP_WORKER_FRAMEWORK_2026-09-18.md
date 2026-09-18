# Nexus Generic Temporary Worker Framework

## Status

`PASS_REAL_BOUNDED` for the provider-neutral framework and Mac canary.
Kaggle is represented as an adapter but is `BLOCKED_EXTERNAL` because this
environment has no Kaggle CLI and no configured Kaggle credential. Modal was
reused, not replaced, and no paid or remote workload was launched.

## Existing work reused

The repository already contained the strongest pieces of this architecture:

- `scripts/nexus_agent_platform/remote_worker.py`: bounded
  `nexus.remote-job.v1` / `nexus.remote-result.v1` envelopes, HMAC request
  validation, capability allowlisting, tenant validation, health, duplicate
  protection, and an HTTP provider.
- `deploy/modal/modal_app.py`: existing deployed Modal CPU worker and existing
  bounded creative GPU capability.
- `deploy/remote-cpu-worker`: fixed-command container with no shell authority.
- Existing evidence-ingestion and receipt/provenance persistence patterns.

The new `temporary_worker_framework.py` is a façade and generic contract layer
around these pieces. It does not create a scheduler or a second control plane.

## Canonical contracts

`WorkerJob` now carries worker type, production package/campaign correlation,
bounded inputs, resource requirements, environment requirements, runtime limits,
provider preferences/exclusions, and batch signatures.

`WorkerResult` carries provider/job identity, lifecycle status, timing phases,
artifacts, SHA-256 hashes, logs, warnings, errors, tool/model versions,
resource usage, external mutations, and cleanup status.

`EnvironmentManifest` describes a rebuildable empty-start environment rather
than relying on hidden provider state.

The provider interface exposes probe, prepare, launch, input staging,
environment restore, execute, output collection, receipt writing, cleanup,
cancel, and health.

## Provider truth

| Provider | State | Notes |
| --- | --- | --- |
| Mac | Available | Local bounded process adapter; canary passed |
| Oracle | Not proven | Existing Oracle/Hermes mechanisms remain untouched |
| Modal | Existing deployed capability | Reuses `remote_worker` contract and `HttpRemoteWorkerProvider`; execution not run |
| Kaggle | Blocked external | No CLI, token, or `~/.kaggle/kaggle.json` present |

There is one provider registry. It reports capability and authorization truth;
it does not choose jobs. Resource Governor decision logic remains inactive.

## Mac canary

Canary job: `SMOKE_TEST_V1`, provider `mac`, bounded deterministic JSON
transformation. It staged `input.json`, launched a child process in its own
temporary working directory, returned:

- `result.json`, SHA-256
  `fe6a414f148768781e7c2e3df4c899d696b827f300571da456b5f7d45afdc12c`
- `artifact.txt`, SHA-256
  `699f78ec34b95e8737333122bc282d1cc557b5211ab5ee2e819a4ac60f74f1a3`

Status was `SUCCEEDED`, runtime approximately `0.108s`, and cleanup passed.
The receipt was written through the bounded receipt path; temporary execution
files were removed. No client data, credentials, or production state entered
the canary.

## Kaggle adapter and boundary

The Kaggle adapter implements the same provider interface and reports
`quota_known=false` rather than inventing quota. It can prepare manifests and
returns `BLOCKED_EXTERNAL` when authorization/CLI is absent. It does not own
Nexus state, sessions, queues, campaign data, assets, or receipts.

Required human/external action for a real Kaggle canary: configure an approved
Kaggle CLI/API credential and confirm a bounded CPU notebook/job launch path.
No GPU, model download, or quota consumption was attempted.

## Artifact and cleanup lifecycle

Provider output is collected, hashed, validated, and linked to the WorkerJob.
Creative output remains destined for the existing `creative_assets`/governed
ingest path. Cleanup is attempted on success, failure, and timeout; canonical
artifacts are not deleted by cleanup. Secrets are not placed in manifests,
logs, receipts, or artifact metadata.

## Compatibility with the restaurant production package

The existing `ProductionReadiness` contract remains the gate before a future
WorkerJob. The WorkerJob can carry the production package and readiness IDs;
this framework only inspects/executes bounded worker jobs and does not generate
media in this certification.

## Measurement, quota, and batching

The result schema exposes startup, setup, model-load, execution, transfer,
cleanup, total runtime, CPU/RAM/GPU/VRAM/storage, quota, cost, and success
measurements. Unknown values remain `UNKNOWN`.

Batch compatibility compares worker class, environment signature, dependency
signature, model signature, and GPU class. A grouping test passed. This is a
future Governor input, not a scheduler.

## Tests

Five focused Python tests passed, covering Mac artifact hashing/cleanup,
provider registry, Kaggle blocked behavior, batch compatibility, and rebuildable
environment manifests. Python compilation passed. No external mutations,
publication, customer contact, money spent, or media generation occurred.
