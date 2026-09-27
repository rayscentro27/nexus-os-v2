# Nexus Reproducible Cloud Notebook Worker — 2026-09-27

## Scope

Systems now has a provider-neutral recipe/asset/job contract layered on the
existing temporary worker framework. The first recipe is a clean-runtime GPU
diagnostic; the first avatar candidate remains MuseTalk because that is the
previously selected sandbox candidate, not because it has been approved for
production.

## Registered capability

- Permanent objective: `systems-permanent-cloud-notebook-worker`
- Recipe library: `configs/systems_worker_recipes.json`
- Notebook template: `configs/systems_notebooks/gpu-environment-diagnostic-v1.ipynb`
- Adapter module: `scripts/nexus_agent_platform/systems_notebook_worker.py`
- Existing provider abstraction: `temporary_worker_framework.py`
- Existing provider registry: Mac, Oracle status, existing remote control plane,
  and Kaggle

Recipes carry a version, runtime, dependency/system-package contract, model
revision gate, input/output contract, resource class, and validation procedure.
Model recipes do not run while their revision/license gate is unresolved.

## Asset gate

The approved source directory is `~/Downloads` for the initial workflow.
Discovery accepts only explicit Nova names (`nova_master.*`, `nova_source.mp4`,
and explicit `nova_*` audio names), hashes each accepted file, records MIME and
size, and never substitutes arbitrary media. The inspected directory contained
no approved Nova image/video/audio asset. Two unrelated MP3 files were excluded.

## Diagnostic execution

The clean diagnostic package ran locally without altering the production Mac:

- ffmpeg probe: pass
- disk probe: pass
- Python/platform probe: pass
- Torch probe: unavailable because Torch is not installed locally
- GPU claim: not made
- model import: intentionally not attempted
- output: `diagnostic_report.json` and `run_manifest.json`
- cleanup: temporary package removed

Kaggle probing returned `KAGGLE_AUTH_REQUIRED` because neither the Kaggle CLI
nor supported credentials were present. No credentials were printed, embedded,
or created. The existing remote-control-plane registration was detected, but
the current allowlist does not authorize arbitrary avatar execution. This is a
truthful provider boundary, not a failed Nova benchmark claim.

## Nova benchmark boundary

MuseTalk remains `BLOCKED_PENDING_PINNED_DEPENDENCY_AND_MODEL_LICENSE_REVIEW`.
The prior audit found no approved Nova reference asset and no complete pinned
weights/data-license package. Therefore no `nova_test.mp4` was created and no
video approval or grounded Creative evaluation was claimed. Once a human
provides an approved asset and Kaggle authentication/model-license gates are
resolved, the same job envelope can submit, monitor, collect, hash, ffprobe,
and persist a run manifest without Creative knowing Kaggle mechanics.

## Recovery model

The adapter boundary is `PREPARE → PUSH → START → STATUS/LOGS → OUTPUT →
VERIFY`, with bounded provider status checks and persisted job receipts. A
provider failure is kept separate from recipe state. The diagnostic recipe is
the safe first recovery action for a `kernelworkerstatus.error`-style failure;
the complete avatar workload is not repeatedly relaunched without evidence.
