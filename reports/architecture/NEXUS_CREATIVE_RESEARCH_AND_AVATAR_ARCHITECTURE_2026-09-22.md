# Nexus Creative Research and Avatar Architecture

## Decision

`CREATIVE_RESEARCH_PASS=PASS_REAL_BOUNDED`

`PRODUCTION_CHANGES_MADE=NO`

Do not expand Creative prompt architecture now. Preserve the current Director, Art Director, Prompt Architect, Meta browser path, reference research, web render canvas, Admin Review, and open/directed mode boundary.

## Ownership boundary

Marketing owns: objective, audience, offer, channel, dimensions, CTA requirement, verified claims, brand assets, and distribution format.

Creative owns: campaign idea, story, emotion, visual language, artistic style, hook, character choice, humor, metaphor, pacing, sound, cinematography, and execution.

Performance systems provide evidence after execution. They must not silently turn metrics into mandatory creative instructions.

## Research inventory

| Capability | Current Nexus state | Recommended next role |
|---|---|---|
| Creative ideation/direction | PASS_REAL_BOUNDED | Preserve |
| Art direction | PASS_REAL_BOUNDED | Preserve; feed diverse references |
| Prompt architecture | PASS_REAL_BOUNDED | Preserve; no new restrictions |
| Reference research | PASS_REAL_BOUNDED via Inspo | Preserve; add sources only after read-only evaluation |
| Image/video execution | Meta browser PASS_REAL_BOUNDED | Preserve primary; add lab comparison |
| Web/funnel render | PASS_REAL | Preserve |
| Visual critique | Partial; real-pixel input required | Add read-only vision adapter when authorized |
| Performance analytics | Partial/scattered | Normalize Meta/Instagram/YouTube read-only metrics |
| Persistent avatar | Not configured | Define contract; run synthetic canary |
| Voice identity | Not configured | Add consented `VOICE_ID` lane after avatar proof |

## Three stack options

### Option A — Lowest cost

- Creative Director / Art Director / Prompt Architect: existing Nexus router.
- Image identity: ComfyUI + IP-Adapter/InstantID experiment.
- Video: existing Meta browser or local Wan lab workflow.
- Avatar: stylized synthetic reference-sheet character.
- Voice: no cloning initially; captions or generic TTS only.
- Web: existing render canvas.
- Analytics: YouTube Analytics plus manually/securely imported Meta insights.
- Research: Inspo MCP + platform-native Creative Centers.

Expected cost: low after GPU availability. Setup burden: high. Reliability: medium for image, low-to-medium for identity-consistent video until tested.

### Option B — Balanced

- Meta browser remains primary image/video/funnel execution.
- Run one hosted reference-character lab test, preferably Runway Gen-4 References or an equivalent authorized service.
- Use Inspo MCP and read-only performance adapters.
- Use a synthetic avatar contract with reference images and versioning.
- Use YouTube/Meta/TikTok analytics only in read-only mode.

Expected cost: moderate usage-based. Setup burden: medium. Reliability: higher for short campaign production, with vendor/API/session risk.

### Option C — Higher capability

- Creative remains Nexus-owned and provider-neutral.
- Hosted reference-character/video provider for visual consistency.
- Hosted talking-avatar provider for presenter campaigns.
- Consent-managed voice provider.
- Meta Marketing API/Instagram insights/TikTok/YouTube analytics adapters.
- Multimodal visual/performance critic with artifact-level receipts.

Expected cost: paid subscriptions/API usage. Setup burden: medium-high. Reliability: high for specialized lanes, but cost, legal, provider lock-in, and identity-consent risk increase.

## Recommended sequence

1. Implement only the avatar identity contract and a synthetic-character drift canary.
2. Test one open ComfyUI image reference workflow against the existing Meta browser path; compare identity persistence, time, and output quality.
3. Add a read-only performance schema for Meta/Instagram/YouTube; do not connect writes or live queue actions.
4. Evaluate one hosted reference system only if the open canary fails the quality/reliability gate.
5. Add voice only after avatar identity and consent governance pass.

## Measurable gates

- `AVATAR_REFERENCE_REUSE=PASS` if the same avatar remains recognizable in 4/5 bounded image/video/web tests without manual face replacement.
- `AVATAR_DRIFT_RATE` is recorded per asset, not inferred from prompt text.
- `VOICE_IDENTITY_REUSE=PASS` only with consent receipt and independent human/automated similarity review.
- `PERFORMANCE_FEEDBACK=PASS` only when platform metrics have source IDs, date ranges, attribution boundaries, and no invented conversions.
- `CREATIVE_OWNERSHIP=PASS` only if the system preserves Creative’s concept freedom and treats analytics as evidence, not a template.

## Sources

- [ComfyUI](https://github.com/Comfy-Org/ComfyUI)
- [IP-Adapter](https://arxiv.org/abs/2308.06721)
- [LivePortrait](https://github.com/KwaiVGI/LivePortrait)
- [Wan2.1](https://github.com/Wan-Video/Wan2.1)
- [Runway Gen-4 References](https://help.runwayml.com/hc/en-us/articles/40042718905875-Creating-with-Gen-4-Image-References)
- [Meta Reels guidance](https://www.facebook.com/business/ads/facebook-instagram-reels-ads)
- [TikTok Creative Best Practices](https://ads.tiktok.com/business/en/blog/creative-best-practices-top-performing-ads?redirected=1)
- [YouTube Shorts discovery](https://support.google.com/youtube/answer/11914225)
- [YouTube Analytics](https://developers.google.com/youtube/analytics)
