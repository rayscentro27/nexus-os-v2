# Nexus Creative GPU Worker — Phase P-B

Status: implementation complete; live GPU image certification blocked by Modal GPU capacity.

## Gate and cost truth

The authenticated Modal workspace is `goclearonline` on Starter. Current official Starter pricing publishes `$30/month` included compute credit: <https://modal.com/pricing>. Modal billing is read with the billing summary CLI documented at <https://modal.com/docs/cli/latest/billing>.

The final pre-run observation was `$0.06` metered and `$0.00` billed, with `$0.06` credits applied. The pilot hard cap was `$0.25` additional metered compute. The final observed month total was `$0.13` metered and `$0.00` billed, with `$0.13` credits applied. This supports an estimated remaining included capacity of `$29.94` at the final pre-run snapshot, classified as `ESTIMATED_FROM_PLAN_ALLOWANCE_AND_CURRENT_USAGE`, not an authoritative balance.

No plan upgrade, payment-method change, persistent GPU volume, or paid GPU capacity was added.

## Worker boundary

`deploy/modal/creative_gpu_app.py` defines the separate `nexus-creative-gpu-worker` Modal app. It exposes only the fixed `creative.image_generate` function, with one container, one GPU, concurrency one by construction, bounded timeout, and scale-to-zero. The existing CPU worker remains deployed and was not modified operationally.

The worker accepts only the Nexus remote-job envelope, validates tenant/capability/workflow/model/limits, verifies the existing signed request, and runs a fixed local ComfyUI command. There is no public ComfyUI UI or port 8188, no generic shell, no arbitrary workflow upload, no arbitrary model selection, and no custom nodes.

## ComfyUI and model gate

ComfyUI was pinned to `v0.31.0` from the official repository, which is GPL-3.0: <https://github.com/Comfy-Org/ComfyUI>. The pilot workflow is `goclear_editorial_image_v1`, core nodes only: checkpoint loader, text encoders, empty latent, sampler, VAE decode, and save image.

The single model is Stability AI SDXL Base 1.0, from <https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0>, using the publisher’s `CreativeML Open RAIL++-M` license. Because current commercial applicability for this specific checkpoint was not conclusively established in the repository’s business context, the worker labels it `EVALUATION_ONLY`; no public/commercial distribution is enabled.

## Live attempt

The complete control path was implemented through the existing provider-neutral Modal adapter and the Phase O Creative Studio contracts. The T4 attempt was queued for unavailable `GPU_T4` capacity and was stopped before generation. A bounded L4 fallback was also queued and stopped before generation. No PNG, creative asset, or receipt was accepted. No model or ComfyUI runtime was added to Git.

Because no image was produced, duplicate suppression and material-version behavior are covered by deterministic local request-fingerprint tests/runner logic, but the live GPU success gate remains open. The correct certification is therefore `GPU_CREATIVE_WORKER_READY=NO` and `COMFYUI_GPU_CREATIVE_READY=DEFERRED`, not YES.

## Governance

Accepted GPU assets are `nexus.creative-asset.v1`, `REVIEW_REQUIRED`, retain Growth/Opportunity/evidence refs, record workflow/model/license metadata and hashes, and set `external_action_performed=false`. Mission Control reads GPU state through the existing Creative Studio portfolio. Publishing, messaging, ads, financial actions, and Ray approval remain outside the worker.
