# Nexus Creative Capability Research

Date: 2026-09-22  
Scope: research and architecture only. No tools installed, no routing changed, no production campaign published, and no money spent.

## Executive finding

Nexus should pause further Creative-architecture expansion. The current internal stack already covers ideation, direction, prompt translation, principle-only reference research, browser-based Meta production, web rendering, provenance, and review. The highest-value missing capabilities are:

1. a persistent avatar/character identity layer;
2. a read-only performance-feedback layer tied to platform insights;
3. a controlled research layer for current creative patterns and competitor references;
4. a small number of execution adapters selected by evidence rather than more hand-built prompt skills.

The main recommendation is to preserve Creative ownership and add capability adapters around it. Marketing supplies the business job and constraints. Creative determines the solution. Performance data critiques outcomes after release; it does not dictate the next concept mechanically.

## Current Nexus stack

### Existing Creative intelligence

- Creative Director with bounded provenance and divergence testing.
- Creative Critic and response-strategy analysis.
- Art Director with principle-only visual reference input.
- Prompt Architect with explicit open/directed Meta modes.
- External Inspo MCP reference research, read-only and principle-only.
- Model router with task classes and cost/token/latency receipts.
- Visual critique contract that refuses pixel-level PASS without real image/frame input.
- Creative Lab, variation engine, media library, and campaign lineage artifacts.

### Existing Creative execution

- Meta.ai authenticated browser path for image/video/funnel work.
- Chromium web render canvas with desktop/mobile screenshots.
- Existing local/remote video experiments, including Modal/Wan evidence and known gaps.
- Static image/video assets and Admin Review Center.
- Partial AVATAR/VOICE desks in the department registry, but no certified persistent avatar provider or identity registry.

### Actual gaps

- No canonical `AVATAR_ID` registry with reference assets, voice identity, versioning, and drift checks.
- No certified character-consistency pipeline spanning image, video, web, and social.
- No production-safe voice-consistency lane.
- No read-only adapter that normalizes Meta/TikTok/YouTube creative performance into Creative feedback.
- No proven broad TikTok/Instagram competitor-research feed beyond platform-native/manual sources.
- Current Meta browser production is real but consumer-session limits, retrieval behavior, and automation stability remain dynamic.

## Current performance research

The strongest evidence is platform-owned guidance, not generic “viral formula” content:

- Meta reports that Reels creative built as 9:16 video with audio and safe-zone messaging performed better than image-only comparisons in its cited split-test analysis. This supports a format hypothesis, not a universal creative rule. [Meta Reels ads](https://www.facebook.com/business/ads/facebook-instagram-reels-ads)
- TikTok’s own creative guidance emphasizes TikTok-native vertical treatment, early value communication, hook/body/close structure, sound, text overlays, and creator-native formats. Its cited research says much ad-recall impact occurs in the first six seconds. [TikTok Creative Best Practices](https://ads.tiktok.com/business/en/blog/creative-best-practices-top-performing-ads?redirected=1)
- YouTube states that Shorts ranking responds to whether viewers choose to watch, retention, average view duration, average percentage viewed, and satisfaction signals; its analytics exposes “shown in feed” and “how many chose to view.” [YouTube Shorts discovery](https://support.google.com/youtube/answer/11914225), [Shorts analytics](https://support.google.com/youtube/answer/12942217)
- YouTube’s retention guidance specifically recommends moving later “top moments” earlier when the data supports it, and treats spikes as rewatch/share or possible clarity signals. [YouTube retention](https://support.google.com/youtube/answer/9314415)

Reusable hypotheses for Nexus testing:

- The first visual/audio/text event must establish a reason to keep watching; exact emotion remains Creative-owned.
- Native vertical framing and safe-zone-aware text are execution requirements for Reels/TikTok/Shorts, not concepts.
- Story, humor, surprise, UGC, animation, and polished cinematography should be treated as test families, not a single house style.
- Measure the first choice to watch separately from downstream retention and conversion.
- Do not optimize to CTR alone; pair attention metrics with qualified lead, landing behavior, and claim/compliance QA.

## Platform and research capability findings

### Meta

- Meta Ad Library is useful for public competitor/ad-pattern research, but access and API eligibility must be verified for the account and use case. The Ad Library API exposes search/filter concepts and ad metadata; it is not a universal performance feed. [Meta Ad Library API](https://www.facebook.com/ads/library/api/)
- Meta Marketing API/Insights can expose account/ad/campaign metrics such as impressions, clicks, spend, reach, CTR-related fields, video quartiles, thruplay, conversions, and outbound clicks when authorized. [Meta Marketing API reference](https://developers.facebook.com/docs/marketing-api/insights/)
- The existing Meta browser path should remain the production surface until an API-backed execution adapter is separately proven.

### Instagram

- Instagram Graph/API routes can provide media/account insights and publishing capabilities for eligible professional accounts, but this is distinct from Ads Manager performance and requires app/account permissions. [Instagram API documentation](https://developers.facebook.com/docs/instagram-api/)

### TikTok

- TikTok Creative Center and Top Ads are strong current-reference surfaces for hooks, creator formats, transitions, sounds, and category patterns. They are primarily reference/research inputs, not an automatic proof of GoClear performance. [TikTok Creative Center guidance](https://ads.tiktok.com/business/creativecenter/)
- TikTok’s official guidance supports testing creator-native, vertical, sound-aware, text-overlay, and hook/body/close treatments. [TikTok Creative Codes](https://ads.tiktok.com/business/creativecenter/quicktok/online/tiktok_creative_accelerator/pc/en)

### YouTube Shorts

- YouTube Analytics is the clearest near-term performance source for view-choice, retention, average percentage viewed, spikes, dips, traffic, and subscriber effects. It should feed a read-only Creative performance review adapter. [YouTube Analytics API](https://developers.google.com/youtube/analytics)

## Tool and project research

### High-value open/self-hosted candidates

**ComfyUI** — modular, local/offline node graph and API-oriented workflow surface. It is actively released, supports JSON workflows, custom nodes, video/image workflows, and can disable optional paid API nodes. GPL-3.0 means downstream integration needs deliberate boundary design. Best role: lab execution/orchestration, not Creative intelligence. [ComfyUI](https://github.com/Comfy-Org/ComfyUI), [license](https://github.com/comfy-org/ComfyUI/blob/master/LICENSE)

**IP-Adapter / InstantID ComfyUI nodes** — reference-conditioned identity/style controls that can improve image identity persistence without training a full model. They are promising for lab tests but require GPU/model downloads and careful license review per checkpoint. Best role: avatar image reference experiments. [ComfyUI IPAdapter Plus](https://github.com/cubiq/ComfyUI_IPAdapter_plus), [ComfyUI InstantID](https://github.com/cubiq/ComfyUI_InstantID), [IP-Adapter paper](https://arxiv.org/abs/2308.06721)

**LivePortrait** — open research implementation for portrait animation and driving-video/audio-style motion. It is useful for controlled talking-head experiments but is not by itself a complete brand-avatar registry or campaign system. [LivePortrait](https://github.com/KwaiVGI/LivePortrait), [paper](https://arxiv.org/abs/2407.03168)

**Wan / ComfyUI Wan workflows** — credible open image-to-video and text-to-video path with reference-image workflows. It is GPU-heavy and quality/identity consistency need a Nexus-specific canary. [Wan2.1](https://github.com/Wan-Video/Wan2.1), [ComfyUI Wan blueprint](https://github.com/Comfy-Org/ComfyUI/blob/master/blueprints/Image%20to%20Video%20%28Wan%202.2%29.json)

**HunyuanVideo-Avatar** — interesting audio-driven/avatar research, but the Tencent Hunyuan Community License has territory, distribution, and usage constraints that make it unsuitable for immediate production adoption without legal review. [HunyuanVideo-Avatar](https://github.com/Tencent-Hunyuan/HunyuanVideo-Avatar), [license](https://github.com/Tencent-Hunyuan/HunyuanVideo-Avatar/blob/main/LICENSE)

**InstantCharacter** — technically relevant for character persistence, but its published license explicitly limits use to academic, research, and education and prohibits commercial/production use. It is research-only for Nexus. [InstantCharacter](https://github.com/Tencent-Hunyuan/InstantCharacter), [license](https://github.com/Tencent-Hunyuan/InstantCharacter/blob/main/License.txt)

### External/reference candidates

**Runway Gen-4 References** — strongest documented hosted candidate for single-reference character/world consistency across images and video. It supports reusable references and API access, but it is paid/proprietary and requires a separate commercial decision. [Gen-4 research](https://runway.com/research/introducing-runway-gen-4), [References documentation](https://help.runwayml.com/hc/en-us/articles/40042718905875-Creating-with-Gen-4-Image-References), [API](https://runway.com/news/introducing-runway-api-for-gen-4-images)

**Kling Elements** — documented reference-image element consistency for video, useful as a lab comparison. API/commercial terms and account access require verification before adoption. [Kling character consistency](https://kling.ai/quickstart/ai-video-character-consistency)

**HeyGen Avatar/Avatar V** — strong hosted talking-avatar path with video-reference appearance, expression, and voice behavior. It is paid/proprietary and appropriate only if the campaign needs a presenter/avatar rather than general visual storytelling. [Avatar V technical report](https://dynamic.heygen.ai/www/Paper%20Links/avatarv_tech_report.pdf)

**ElevenLabs** — mature hosted voice API with voice-cloning endpoints. It should be treated as a consented voice-identity provider, not as an automatic permission to clone any person. [voice cloning API](https://elevenlabs.io/docs/api-reference/voices/ivc/create)

**Meta Ads MCP servers** — several open-source MCPs expose Meta account discovery, creative inspection, insights, and sometimes write operations. They are performance/operations candidates, not creative-originating systems. The read-only boundary is essential because several projects expose campaign mutation tools. [mlg-meta-mcp](https://github.com/iammalego/mlg-meta-mcp), [byadsco meta-ads-mcp](https://github.com/byadsco/meta-ads-mcp), [hashcott meta-ads-mcp](https://github.com/hashcott/meta-ads-mcp), [read-oriented adstream-mcp](https://github.com/ramadhanidiwanda-alt/adstream-mcp)

## What current evidence does not prove

- No researched open-source stack proves persistent character identity across image, multi-shot video, voice, landing pages, and social output without a dedicated reference registry and QA loop.
- No public competitor-research feed automatically provides reliable performance outcomes for competitors; public ad libraries mostly expose creative presence/metadata, not true conversion performance.
- “AI avatar” marketing claims are not enough to certify voice consent, commercial rights, or identity stability.
- An open-source model’s code license does not automatically grant commercial rights to weights, checkpoints, training data, or generated likenesses.

## Research conclusion

The next implementation should be a narrow, read-only capability test, not another broad architecture expansion:

1. define and persist the avatar contract;
2. create a reference-sheet/identity QA canary using existing approved assets or a clearly synthetic character;
3. compare one open ComfyUI reference workflow against one already-authorized hosted route;
4. normalize only read-only Meta/Instagram/YouTube performance data;
5. let Creative interpret the evidence rather than convert metrics into automatic concepts.

No tool should be adopted into production from this research alone.
