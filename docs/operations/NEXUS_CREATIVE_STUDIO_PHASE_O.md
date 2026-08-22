# Nexus Creative Studio — Phase O Certification

Status: `CREATIVE_STUDIO_FOUNDATION_READY=YES` (internal, non-public production layer)

Phase O reuses the existing Creative Lab, Creative Studio feeder, deterministic
design helpers, quality scoring, approval records, `task_requests`,
`nexus_events`, and the existing publishing firewall. It adds only the governed
brief/asset/receipt read model needed to connect the existing Phase M growth
experiment to internal creative work. No second scheduler, operator, approval
store, work-order system, or publishing system was created.

## Canonical contracts

- `nexus.creative-brief.v1` — links a brief to Growth, Opportunity, research,
  evidence, offer, CTA, brand status, prohibited claims, and the Phase L target
  metric.
- `nexus.creative-asset.v1` — stores internal copy, storyboard, image specs, and
  rendered media metadata, including source refs, hashes, quality findings,
  license metadata, approval state, and `external_action_performed=false`.
- `nexus.creative-render-result.v1` — compact render receipt; binaries remain in
  runtime-generated storage and are not committed to Git.

The live brief was created from the Phase M evidence-backed experiment
`growth_c774e2e42583448b844c4a97a80f5dcf`, the Phase K opportunity
`opp_5700d95807d82a3bab55c23d`, and public evidence `ev-8874c37fddb5461287d2`.
It remains `NEEDS_RAY_REVIEW`; no approval was fabricated.

## Internal copy and render

The pilot produced a copy package, storyboard, image prompt/layout specs, and a
real silent MP4 using the allowlisted template
`goclear_readiness_explainer_v1`. The render is 1080×1080, 8 seconds, 30 fps,
H.264, and uses only deterministic shapes/text. The artifact is retained under
runtime-generated Creative Studio storage with content and file hashes. The
asset is `REVIEW_REQUIRED` and has no public distribution path.

The renderer accepts only the fixed repository-controlled template and bounded
dimensions/duration. Invalid templates fail closed. Exact requests are
deduplicated; material content changes produce a new asset fingerprint/version.
The local pilot used Remotion for browser composition and a fixed macOS
AVAssetWriter encoder because the installed Homebrew ffmpeg binary was not
usable on this host. Cost is classified `LOCAL_COMPUTE`; no paid worker or GPU
was provisioned.

## Remotion gate

Official sources reviewed: [Remotion repository](https://github.com/remotion-dev/remotion),
[Remotion license](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md),
and [official releases](https://github.com/remotion-dev/remotion/releases?after=v2.2.0).
The isolated pilot pins Remotion `4.0.503`. Commercial-license eligibility for
Nexus/GoClear was not conclusively established, so the disposition is
`REMOTION_LICENSE_STATUS=EVALUATION_ONLY`; this artifact is internal and
non-public. No license was purchased and no recurring spend was authorized.

## ComfyUI gate

The [official ComfyUI repository](https://github.com/Comfy-Org/ComfyUI) was
reviewed. Its software license, model/checkpoint licenses, and custom-node
licenses are separate decisions. The current Nexus worker is CPU-only and no
bounded GPU resource is configured. No ComfyUI checkout, model, checkpoint,
LoRA, VAE, workflow pack, or custom node was installed. The truthful
disposition is:

`COMFYUI_GPU_CREATIVE_READY=DEFERRED`

Future `creative.image_generate` work must use Nexus-owned allowlisted
workflows, separately reviewed model licenses, pinned hashes, denied-by-default
custom nodes, bounded runtime, and Ray-approved compute budget.

## Governance and safety

Creative Studio can draft, score, organize, and render internal review assets.
Ray review remains required before public use. Website publishing, social
posting, email/SMS, ad activation, and spend are blocked. No PII, payment data,
credentials, or worker secrets enter the brief, asset, receipt, Mission
Control, or Hermes read model. Creative failure is optional and does not make
core runtime unhealthy.

Mission Control exposes Creative Studio as optional with asset counts, latest
render, Remotion availability, ComfyUI deferral, GPU state, receipt, and public
actions blocked. Hermes reads the same canonical asset portfolio and reports
that nothing has been published.

Browser/UI certification was not performed because no authenticated browser
session was available; the canonical read model and safety boundary were
certified directly.
