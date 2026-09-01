# WP8.11A Creative Multimodal / Nova Avatar Architecture Audit

CAMPAIGN=HG-WP8.11A-CREATIVE-MULTIMODAL-NOVA-AVATAR-RESOURCE-ARCHITECTURE-AUDIT-20260901-01
START_HEAD=8a7179558e92563bd97bcf4d197d2220092cf063
END_HEAD=REPORT_COMMIT
PUSHED=YES
ORIGIN_MAIN=REPORT_COMMIT

## Decision

CREATIVE_MULTIMODAL_ARCHITECTURE_AUDIT_READY=YES
CREATIVE_REUSE_ORDER_ENFORCED=YES
CREATIVE_NEW_INSTALLS=0
WP8_6_TO_WP8_10_UNCHANGED=YES

This is an audit and design result only. No Creative Department runtime, provider subscription, public publishing, ad spend, social posting, outreach, deployment, or live-authority change was performed.

## Current state

NEXUS_CREATIVE_FOUNDATION_AUDITED=YES
PRIOR_CREATIVE_RESEARCH_AUDITED=YES

Existing reusable surfaces are `scripts/nexus_agent_platform/creative/lab.py`, `studio.py`, `intelligence.py`, `gpu.py`; `scripts/creative/*`; `scripts/marketing/build_landing_page_experiments.py`; `scripts/marketing/build_short_video_script_queue.py`; `tools/creative/remotion`; `src/components/NexusCreativeStudioWorkspace.jsx`; approval/review lanes; and the existing Creative Director, Marketing Director, and SEO Director skills. Their status is partial/draft/internal, not production creative or publishing capability. The existing Lab’s three-territory distinctiveness check is the right anti-cookie-cutter seed.

HERMES_CREATIVE_CAPABILITIES_AUDITED=YES
HERMES_VERSION=0.20.0
HERMES_SOURCE_COMMIT=3c27eb6234bf91b8ceee9e9071591b31e9b148cb
HERMES_NATIVE_CREATIVE_CAPABILITIES=multimodal model attachment metadata in configured model catalog; browser/CDP/Camofox supervised routes; MCP client; skills; local files; image-generation and video-generation adapters; TTS/STT helpers; FFmpeg-adjacent media handling. Capability availability is not equivalent to a configured provider or proven rendered output.

CREATIVE_SKILL_REGISTRY_AUDITED=YES
CREATIVE_MCP_RESOURCES_AUDITED=YES
CREATIVE_BROWSER_CONTROL_AUDITED=YES
CREATIVE_SKILLS=Creative Director, Marketing Director, SEO Director; available skill infrastructure is file-backed and permissioned. No new persistent Creative agent is recommended.
CREATIVE_MCP_STATUS=Configured MCP is `nexus_mcp` and `google_mcp`; neither is a Creative image/video/avatar provider. Vibe/other Creative MCP is not proven configured or callable.
CREATIVE_BROWSER_STATUS=Supervised browser/CDP/session tooling exists; authenticated Meta AI or Higgsfield automation was not logged into or proven. CAPTCHA, UI drift, terms, download provenance, and session expiry make unattended use unsuitable as canonical.

## External audit findings

META_AI_CREATIVE_RESOURCE_AUDIT=PASS
META_AI_RECOMMENDED_ROLE=SUPERVISED_ONLY / OPTIONAL_CREATIVE_LANE; use only through a legitimate authenticated user session or official supported interface if later verified; never scrape around controls or make it a required dependency.

HIGGSFIELD_RESOURCE_AUDIT=PASS
HIGGSFIELD_RECOMMENDED_ROLE=BROWSER_RESOURCE / OPTIONAL_PAID_RESOURCE; do not subscribe in WP8.11A. Higgsfield states users own outputs and may use them commercially, while its terms also impose content, likeness, model-training, and service-use restrictions; legal review remains required. Its official GitHub organization exposes SDK/CLI repositories, but that does not prove an unrestricted generation backend.

OPEN_HIGGSFIELD_CANDIDATES_AUDITED=YES
OPEN_HIGGSFIELD_DECISION=REJECT_AS_SELF_HOSTED_ENGINE / REFERENCE_ONLY_AS_UI_PATTERN. The reviewed Open-Higgsfield-AI repo requires a Muapi API key and routes generation to external models; it is not an autonomous self-hosted replacement.

IMAGE_STACK_AUDIT=PASS
COMFYUI_RESOURCE_AUDIT=PASS — candidate only, not installed/configured. ComfyUI offers API/workflow modularity and macOS support, but its repository is GPL-3.0 and model/custom-node licenses remain separate.
VIDEO_GENERATION_STACK_AUDIT=PASS
VIDEO_COMPOSITION_STACK_AUDIT=PASS — FFmpeg is installed; Remotion is an isolated pinned pilot; deterministic composition should own captions, sizing, scenes, audio mix, and metadata.
OPEN_SOURCE_VIDEO_AUDIT=PASS — Wan2.1 is a credible reference/component candidate with Apache-2.0 model licensing as stated by its repository, but practical inference needs GPU/large memory and model/dependency review. Hosted video providers remain optional paid/browser lanes.

NOVA_AVATAR_ARCHITECTURE_AUDITED=YES
OPEN_SOURCE_AVATAR_STACK_AUDIT=PASS
LIP_SYNC_STACK_AUDIT=PASS
VOICE_STACK_AUDIT=PASS
NOVA_VISUAL_IDENTITY_CONTRACT_DESIGNED=YES
AVATAR_DECISION=No current local proof justifies selecting LivePortrait, MuseTalk, EchoMimic, Hallo, or SadTalker as production canonical. They remain sandbox candidates. MuseTalk’s repository describes MIT code and commercial model use but calls out separate third-party model/data licenses; LivePortrait’s commercial-license clarity is insufficient for automatic adoption. Canonical fallback is static Nova portrait + approved voice + deterministic motion graphics until a sandbox benchmark proves an avatar lane.

## Canonical architecture recommendation

CANONICAL_CREATIVE_ARCHITECTURE=RECOMMENDED

| Capability | PRIMARY | FALLBACK | Current status | WP8.11B action |
|---|---|---|---|---|
| creative reasoning | Hermes Creative Director skill + Alpha evidence | Nova brief | available, not department-complete | add brief/territory contracts |
| copy | bounded Nexus draft generators + strong model route | deterministic templates | draft-only | wrap with claim/brand critic |
| landing page | Nexus React/Vite/Tailwind + existing experiment builder | static local HTML | implemented partial | add rendered screenshot QA |
| image | provider-neutral router; existing GPU/Modal adapter | image concept/spec | configured partial | benchmark one approved provider |
| video generation | optional hosted/API lane | storyboard + stills | not proven | adapter only after license/cost gate |
| composition | FFmpeg + isolated Remotion | no-render package | locally available | canonical deterministic compositor |
| avatar | provider-neutral sandbox lane | static Nova portrait + voice | not proven | benchmark identity/lip-sync candidates |
| lip sync | avatar adapter output | voice-over + captions | not proven | separate benchmark, not implicit |
| voice | existing Hermes/Nexus TTS routes | caption-only | available/provider-dependent | pin lawful consistent Nova voice |
| browser creative | supervised browser route | manual operator step | available, not proven for Meta/Higgsfield | keep optional and supervised |
| critic | multimodal model reviewing screenshots/frames | deterministic lint + human review | designed, not implemented here | add artifact/frame critic |

Primary canonical control plane remains Nexus governed state, work orders, receipts, approvals, and immutable creative versions. External tools are adapters/resources, never authorities.

## Contracts and desks

CREATIVE_TERRITORY_CONTRACT=DESIGNED — territory_id, audience, human insight, problem, emotional/rational angle, promise, mechanism, visual world, hook family, channel fit, risks, evidence refs.
CREATIVE_DIRECTOR_ROLE=DESIGNED — interpret brief, load Alpha/Growth/customer evidence, define distinct territories, commission assets, reject generic output.
CREATIVE_CRITIC_ROLE=DESIGNED — independent originality, specificity, hierarchy, channel, brand, claim, CTA, and genericness review; never same-context self-approval.
CREATIVE_BRAND_GUARDIAN_ROLE=DESIGNED — brand context, voice, visual identity, forbidden use, temporary venture brand, channel adaptation.
CREATIVE_CLAIM_REVIEW_ARCHITECTURE=DESIGNED — claims are checked against source refs and compliance rules for copy, ads, social, video, and Nova scripts.
CREATIVE_GENERICNESS_DETECTION_ARCHITECTURE=DESIGNED — n-gram/structure/signature repetition, semantic similarity, generic phrase lint, unsupported superlatives, customer-language coverage, competitor-pattern overlap, and visual-template repetition.
CREATIVE_DESK_ARCHITECTURE=DESIGNED — Director, Copy, Landing Page, Visual, Social, Video, Avatar, Voice, Critic, Brand, Performance as skills/services, not unnecessary agents.
CREATIVE_MODEL_ROUTING=DESIGNED — AI for territory/copy/storyboard/critique; deterministic Python/TS for IDs, state, versions, dimensions, captions, rendering, provenance, queues, receipts.
MULTIMODAL_CREATIVE_CRITIC=DESIGNED — inspect actual rendered screenshots, generated images, and sampled video frames; source text alone cannot pass visual QA.

FACEBOOK_CREATIVE_ARCHITECTURE=DESIGNED
INSTAGRAM_CREATIVE_ARCHITECTURE=DESIGNED
TIKTOK_CREATIVE_ARCHITECTURE=DESIGNED
YOUTUBE_CREATIVE_ARCHITECTURE=DESIGNED
CREATIVE_CHANNEL_ADAPTER=DESIGNED — strategy → channel-native brief → format asset; never merely resize one artifact.
ALPHA_TO_CREATIVE_TREND_INPUT=DESIGNED — Alpha supplies recent themes, customer language, source families, evidence quality, and caveats; Creative transforms patterns without copying.
CREATIVE_INSPIRATION_TRANSFORMATION=DESIGNED
COMPETITOR_CREATIVE_INTELLIGENCE_ARCHITECTURE=DESIGNED — public pages, YouTube, search, and legitimately accessible ad libraries; capture provenance, abstract patterns, not protected copy.

## Memory, quality, and adaptive integration

VIDEO_CLAIM_HIERARCHY=DESIGNED — VIDEO_CONCEPT → VIDEO_SCRIPT → STORYBOARD → ASSET_PLAN → RENDERED_VIDEO → QA_APPROVED_VIDEO → PUBLISHED_VIDEO.
IMAGE_CLAIM_HIERARCHY=DESIGNED — IMAGE_CONCEPT → IMAGE_PROMPT → GENERATED_IMAGE → QA_APPROVED_IMAGE → PUBLISHED_IMAGE.
LANDING_PAGE_CLAIM_HIERARCHY=DESIGNED — PAGE_CONCEPT → PAGE_SPEC → PAGE_CODE → LOCAL_BUILD → VISUAL_QA → VALIDATION_READY → DEPLOYED → MARKET_TESTED.
CREATIVE_ASSET_MEMORY=DESIGNED — brief, territory, asset/version/parent, change rationale, channel/audience, evidence/performance refs, failure, learning.
CREATIVE_FAILURE_MEMORY=DESIGNED — failed hypothesis, channel, audience, measurement validity, diagnosis, and conditions for revisit.
CREATIVE_PATTERN_MEMORY=DESIGNED — only evidence-backed relationships with sample/context; opinions remain candidates.
CREATIVE_ADAPTIVE_LOOP_INTEGRATION=DESIGNED — creative outcome → WP8.10 diagnosis → failure dimension → new territory/asset version → bounded retest.
GROWTH_CREATIVE_CONTRACT=DESIGNED — Growth owns objective/audience/metric; Creative returns testable asset, variant hypothesis, channel format, and claim provenance.
NOVA_CREATIVE_CONTRACT=DESIGNED — Nova commissions and reviews concise packets; it does not micromanage generation.
NOVA_AVATAR_CREATIVE_PRODUCT=DESIGNED — identity → script → voice → motion/lip sync → scene → composition → captions → QA.
CREATIVE_JAX_BOUNDARY=DESIGNED — Creative owns direction; Jax owns React/render/instrumentation/integration.

## Resource, cost, and safety matrix

CREATIVE_RESOURCE_MATRIX=COMPLETE

| Resource | Location/type | Cost / license | Status | Role/classification |
|---|---|---|---|---|
| Nexus Creative Lab/Studio | local Python | internal / repository | partial, draft-only | primary foundation / WRAP |
| Creative skills | local plugin | repository | available | reasoning / KEEP |
| React/Vite/Tailwind | local frontend | repository deps | available | landing primary / KEEP |
| Playwright/browser | local | repository dep | available | visual QA / ADAPT |
| FFmpeg | `/usr/local/bin/ffmpeg` | system binary | available | compositor / KEEP |
| Remotion | `tools/creative/remotion` | pinned npm; review license | isolated pilot | compositor adapter / ADAPT |
| Hermes image/video adapters | Hermes runtime | provider-dependent | code exists, config-dependent | router candidate / WRAP |
| ComfyUI | external candidate | GPL-3.0 + model licenses | not configured | workflow candidate / SANDBOX_ONLY |
| Wan2.1 | GitHub/model | Apache-2.0 stated; dependency review | not installed | video reference / SANDBOX_ONLY |
| Higgsfield | hosted/browser/API | subscription/unknown by lane | not configured | optional resource / SUPERVISED |
| Meta AI | hosted/browser | terms/access dependent | not proven | optional lane / SUPERVISED |
| LivePortrait/MuseTalk/EchoMimic | GitHub/models | license varies; dependency/model audit | not installed | avatar benchmark / REFERENCE_ONLY |

CREATIVE_RESOURCE_COST_MATRIX=PASS — local deterministic tools are `FREE`/existing; hosted generation is `API_COST` or `SUBSCRIPTION`; unconfigured resources remain `UNKNOWN`, never fabricated.
CREATIVE_HARDWARE_FIT_AUDIT=PASS — Mac is Apple Silicon/ARM64-compatible for ordinary Python/Node/browser/FFmpeg work; diffusion/video/avatar inference is not assumed practical without measured RAM/GPU. Oracle is ARM64 CPU-oriented and not assumed to have a suitable GPU. Hosted GPU is optional, budgeted, and approval-gated.
CREATIVE_PRIVACY_BOUNDARY=DESIGNED — PUBLIC_CREATIVE, INTERNAL_CREATIVE, and CLIENT_SENSITIVE_CREATIVE lanes; no client PII to public research or external creative models.
CREATIVE_COMMERCIAL_LICENSE_AUDIT=PASS — audit code, weights, model cards, datasets, custom nodes, provider terms, likeness, and training restrictions separately before commercial use.

## Matrices and rejected resources

CREATIVE_IMPLEMENTATION_GAP_MATRIX=COMPLETE — the main gaps are canonical asset/territory/version persistence, real rendered visual QA, multimodal critic, provider health/router, avatar benchmark, and channel-native package contracts. Reuse existing state/approval/generation surfaces; add adapters and deterministic QA, not a parallel app.
CREATIVE_REJECTED_RESOURCE_LIST=COMPLETE — reject new persistent Creative agent (duplicate control plane); reject Open-Higgsfield as self-host engine (external API wrapper); reject unlicensed/unclear avatar weights for commercial use; reject blind ComfyUI installation (GPL/custom-node/model coupling); reject browser automation as canonical unattended provider; reject unbounded generation and generic one-template channel resizing.
OPEN_SOURCE_COMPONENTS_TO_ADAPT=FFmpeg composition patterns; Remotion isolated composition patterns; Creative Lab territory/diversity checks; Playwright screenshot QA; ComfyUI API/workflow concepts only after license boundary review.
OPTIONAL_PAID_RESOURCES=Higgsfield and other hosted image/video/avatar providers, only after Ray-approved cost/terms review.
OPTIONAL_BROWSER_RESOURCES=Meta AI/Higgsfield supervised sessions, not unattended canonical dependencies.

## WP8.11B plan

WP8_11B_REAL_E2E_PLAN=DESIGNED for `opp_bffe3378956f40bb9317970938eb3f21` / `individual_vehicle_convenience`: load Growth objective and Alpha evidence; create brief; generate ≥3 distinct territories; critic checks distinctiveness and claims; produce landing-page spec/code; local build and desktop/mobile screenshots; produce Facebook, Instagram, TikTok/Reel, YouTube Short packages; generate image only through a proven approved resource; render video only if real provider/engine succeeds; create optional static-Nova presenter fallback; critique, revise once, persist lineage; no publication.
WP8_11B_IMPLEMENTATION_SEQUENCE=READY — 1 contracts/asset registry; 2 evidence-backed brief; 3 territories and genericness gate; 4 channel adapters; 5 landing build/screenshot QA; 6 deterministic image/compositor lane; 7 optional video; 8 avatar/voice benchmark; 9 multimodal critic; 10 WP8.10 adaptive feedback; 11 bounded after-hours runner.
CREATIVE_AFTER_HOURS_LOOP=DESIGNED — consume accepted Growth briefs/Alpha findings/revision queue; emit internal briefs, territories, drafts, renders, critiques, and versioned revisions; route failures to WP8.10.
CREATIVE_AFTER_HOURS_AUTHORITY=BOUNDED_INTERNAL_ONLY
CREATIVE_AFTER_HOURS_BUDGET=DESIGNED — MAX_BRIEFS=2; MAX_TERRITORIES_PER_BRIEF=4; MAX_LANDING_PAGES=1; MAX_IMAGES=4; MAX_VIDEO_RENDERS=1; MAX_AVATAR_RENDERS=1; MAX_AI_CALLS=12; MAX_CRITIQUE_CYCLES=2; MAX_REVISIONS=1; MAX_RUNTIME=30m; MAX_API_COST=$0 until separately approved.
NOVA_CREATIVE_MORNING_BRIEF=DESIGNED — outputs, strongest territories, revisions, failures, degraded tools, validation-ready artifacts, and Ray-only decisions; no raw prompt/transcript dump.
CREATIVE_NON_GENERIC_ACCEPTANCE_STANDARD=DEFINED — ≥3 strategically distinct territories; channel-native output; actual local rendered page; screenshot critique; real asset only if provider is proven; critique-driven immutable revision; claim provenance; Growth metric handoff; no forced winner; genericness gate PASS.
CREATIVE_CAPABILITY_CLAIM_DISCIPLINE=PASS

## Required field summary

PRIMARY_CANONICAL_COPY_ENGINE=Nexus bounded copy generators + Hermes strong-model route
PRIMARY_CANONICAL_LANDING_PAGE_ENGINE=Nexus React/Vite/Tailwind + existing landing experiment builder
PRIMARY_CANONICAL_IMAGE_ENGINE=provider-neutral Nexus Creative GPU/router adapter; no provider certified yet
PRIMARY_CANONICAL_VIDEO_ENGINE=optional adapter; no canonical generator certified yet
PRIMARY_CANONICAL_VIDEO_COMPOSITOR=FFmpeg, with isolated Remotion adapter
PRIMARY_CANONICAL_AVATAR_ENGINE=none certified; static Nova portrait + voice is the safe fallback
PRIMARY_CANONICAL_LIPSYNC_ENGINE=none certified; sandbox benchmark required
PRIMARY_CANONICAL_VOICE_ENGINE=existing Hermes/Nexus TTS routes
PRIMARY_CANONICAL_BROWSER_CREATIVE_LANE=supervised Hermes browser/CDP route
PRIMARY_CANONICAL_CREATIVE_CRITIC=multimodal model + deterministic lint + approval review

FILES_CHANGED=reports only; audit did not modify runtime code/configuration
TESTS=read-only repository/configuration inspection; no Creative runtime implementation tests applicable
SECRET_SCAN=PASS — no secrets added, no provider login, no credentials in reports
WORKTREE=pre-existing dirty worktree preserved; only WP8.11A reports staged
NEXT_RECOMMENDED_PHASE=WP8.11B Creative Department implementation after Ray review
WAITING_RAY=YES
