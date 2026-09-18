# Nexus Model / Provider / Media Capability & Cost Audit

Audit date: 2026-09-17 (America/Phoenix)

Scope: evidence gathering only. No production model, provider credential, MCP,
retrieval, conversation, scrolling, or media behavior was changed.

## Executive disposition

`MODEL_PROVIDER_AUDIT_STATUS=PARTIAL`

The production Admin Nova route is real and healthy: `nova_admin_server.py` uses
`get_nova_graph()` and `LlmGatewayAdapter`, and the adapter currently reaches
OpenRouter with `openai/gpt-4o-mini`. A launchd-backed probe returned
`PROVIDER_OK`; five additional bounded benchmark calls returned HTTP 200.

This audit does not certify an approved free Nous/Hermes model, a hosted image or
video generator, or a better-than-browser Nova voice. Those remain explicitly
unproven rather than inferred from code or historical reports.

## Runtime architecture and provider inventory

| Provider/path | Transport and evidence | Active now | Classification |
|---|---|---:|---|
| OpenRouter | HTTPS `https://openrouter.ai/api/v1/chat/completions`; launchd-backed adapter; runtime key present | YES | `PASS_REAL` |
| OpenAI direct | No `OPENAI_API_KEY` in the inspected runtime; no direct Admin route | NO | `CONFIGURED_BUT_INACTIVE` / not proven |
| Groq | No `GROQ_API_KEY`; no Admin route | NO | `CONFIGURED_BUT_INACTIVE` / not proven |
| Anthropic | No direct runtime key; no Admin route | NO | `CONFIGURED_BUT_INACTIVE` / not proven |
| Gemini direct | Credential registry entry only; no direct Admin route proven | NO | `DOCUMENTED_ONLY` |
| Oracle Ollama | Existing SSH tunnel/config points to `gemma3:4b`; configured gateway was recorded HTTP 401; local daemon probe did not produce a healthy response | NO | `INSTALLED_NOT_ACTIVE` / `CONFIGURED_NOT_PROVEN` |
| Hermes Agent | Separate Mac/Oracle runtime and shadow/Telegram path; not in Admin Nova request path | NO | `HISTORICAL_ONLY` for Admin transport |
| Local Ollama | `/usr/local/bin/ollama` and model blobs exist; daemon health/list did not complete | NO | `INSTALLED_NOT_ACTIVE` |
| Kaggle/custom | No callable Nexus production route found | NO | `UNKNOWN` |

Credential-registry entries are not evidence of active access. Secrets were not
printed or copied into this report.

### Current Admin Nova

- `EXECUTOR=LlmGatewayAdapter via direct Nexus Nova graph`
- `PROVIDER=OpenRouter`
- `MODEL=openai/gpt-4o-mini`
- `CONTEXT_WINDOW=128,000 tokens` (current OpenRouter catalog record)
- `TOOL_CALLING_SUPPORTED=YES by model catalog; not active as a direct Admin MCP tool surface`
- `VISION_SUPPORTED=YES (text/image/file input in catalog)`
- `STRUCTURED_OUTPUT_SUPPORTED=YES (response_format/structured_outputs in catalog)`
- Current adapter defaults: temperature `0.7`, max output `1024`, one bounded retry.
- Catalog price: `$0.15 / 1M input tokens`, `$0.60 / 1M output tokens`.
- Empirical benchmark usage cost was approximately `$0.000027–$0.000063` per short call,
  with roughly 81–86 input tokens and 25–83 output tokens in the five-call sample.

The OpenRouter model catalog was queried on the audit date. See the [live model
catalog](https://openrouter.ai/api/v1/models) and [OpenRouter model guide](https://openrouter.ai/docs/overview/models).

## Relevant OpenRouter candidates

Prices below are USD per token as returned by the catalog; multiply by 1,000,000
for USD/M tokens. Availability means listed by the catalog, not successful Nexus
production certification.

| Model | Class | Input / output per M | Context | Modalities / tools | Practical use |
|---|---|---:|---:|---|---|
| `openai/gpt-4o-mini` | very cheap/current | $0.15 / $0.60 | 128k | text, image, file; tools and structured output listed | Current Nova, classification, routine extraction, bounded tool routing |
| `google/gemini-2.5-flash` | cheap/normal | $0.30 / $2.50 | 1,048k | text, image, file, audio, video; tools and structured output | Long multimodal research, extraction, synthesis |
| `deepseek/deepseek-flash-latest` | very cheap | $0.15 / $0.60 | 1,048k | text/image; tools and structured output listed | Long-context low-cost analysis; needs Nexus benchmark |
| `deepseek/deepseek-pro-latest` | normal | $0.66–$1.32 / $1.98–$3.96 by catalog window | 1,048k | text; tools, reasoning, structured output | Difficult reasoning and review; cost varies by load window |
| `google/gemini-2.5-pro` | premium | $1.25 / $10 baseline; higher tier above 200k input | 1,048k | text/image/file/audio/video; tools and structured output | High-value multimodal/reasoning escalation |
| `inclusionai/ling-3.0-flash-vl:free` | free | $0 / $0 | 262k | text/image/video; tools listed | Candidate free multimodal lane; not Nexus-proven |
| `nex-agi/nex-n2.5-pro:free` | free | $0 / $0 | 262k | text/image; tools and structured output listed | Candidate free reasoning lane; not Nexus-proven |
| `qwen/qwen3.8-27b:free` | free | $0 / $0 | 262k | text/image/video; tools and structured output listed | Candidate free general/multimodal lane; not Nexus-proven |
| `nvidia/nemotron-3.5-lightning:free` | free | $0 / $0 | 1,000k | text; tools listed | Candidate long-context/tool lane; not Nexus-proven |

The free list is dynamic and free access is subject to provider limits and
availability. No free model was promoted into production. The catalog does not
show a currently usable Nous/Hermes free model under the historical names tested;
`NOUS_HERMES_FREE_STATUS=NOT_PROVEN`.

## Hermes / Nous distinction

`HERMES_AGENT_RUNTIME=separate installed/shadow runtime; not Admin transport`.
Historical repository reports identify Hermes Agent 0.20.x and a `nova_nexus`
profile, while the current Admin trace remains direct Nexus → OpenRouter. The
Oracle Ollama configuration identifies `gemma3:4b`, but its recorded gateway
auth status is HTTP 401. `HERMES_MODEL_OPTIONS=not currently proven callable`.

Hermes Agent is an executor/runtime; a Nous/Hermes model is a model/provider
choice. They must not be conflated. Free model availability, rate limits, and
quality need a separate authenticated probe before Resource Governor use.

## Benchmark evidence

The existing bounded benchmark capture utility was run against the current
`openai/gpt-4o-mini` for five frozen dataset cases. Results: 5/5 HTTP 200,
observed model matched the request, no transport/provider failures, latency
`1.81–8.30s`, and observed cost approximately `$0.000027–$0.000063` per call.
This sample covered casual/opinion behavior only; it is not a complete quality
ranking. The fixture and capture parser already support extraction, structured
output, tool-routing, context, and long-context cases, but those additional
cases were not sent to premium models in this audit.

| Dimension | Current evidence |
|---|---|
| Factual accuracy | Not scored by the five casual cases; require labeled A–H fixtures |
| Instruction following | PASS for captured short replies; broader score pending |
| Tool truth | Production capability-truth tests previously pass, but direct tool calling is not active in Admin |
| Structured output | Model catalog supports it; live benchmark validation pending |
| Latency | 1.81–8.30s in sample; first-call variance is material |
| Retry rate | No retry observed in five calls |
| Token usage | Prompt 81–86 tokens; completion 25–83 tokens in sample |
| Cost | Provider usage records approximately $0.000027–$0.000063/call |

The benchmark suite to use for the next governor phase is: A extraction, B
research summarization, C capability/tool routing, D bounded Nova context, E
Alpha challenge, F small code repair, G multi-document precedence, and H strict
JSON schema. Each run should record HTTP status, latency, input/output tokens,
provider retries, parse validity, factual rubric score, and provider-reported
cost. Do not compare models without the same fixture and prompt.

## Coding executors

| Executor | Availability | Model/provider | Auth/repo/tool evidence | Fit |
|---|---|---|---|---|
| Codex CLI | `/usr/local/bin/codex`, version `0.154.0` | executor is separate from model; route is environment-dependent | local executable; repository access available in this workspace | Strong automation fit; cost/auth depends on selected route |
| OpenCode | `/usr/local/bin/opencode` | not proven | executable found; version/auth probe was not completed safely | Candidate, needs bounded command test |
| Kilo | `/usr/local/bin/kilo` | not proven | executable found; auth/model not proven | Candidate, needs bounded command test |
| Mimo Code | `~/.mimocode/bin/mimo` | not proven | executable found; auth/model not proven | Candidate, needs bounded command test |
| Aider/OpenHands/SWE-agent | no active executable evidence in this audit | — | repository references are candidate documentation | Not current callable executors |

## Local inference and voice

Mac evidence: Intel `x86_64`, macOS 12.7.6, 8 GiB RAM. Ollama is installed
and opaque model blobs exist, but the local daemon/list operation did not return
a healthy inventory. Oracle configuration names `gemma3:4b`, but the configured
gateway health record is HTTP 401. Therefore local inference is not a reliable
current Nova route. Small quantized models may fit the Mac, but latency and
quality are unproven; large multimodal/reasoning models are not a sensible
default on 8 GiB.

### TTS

- Browser `speechSynthesis`: current Nova/Admin voice path, callable in the browser;
  quality and female-voice availability are OS/browser dependent; no fixed voice
  is guaranteed.
- Local `say`: installed macOS command, callable locally, not the Admin Nova
  production path.
- Hermes/Nexus local NeuTTS, KittenTTS, and Piper handlers: code/report evidence
  exists, but optional packages/provider configuration are absent or unproven.
- No configured ElevenLabs, OpenAI TTS, edge-tts, or other hosted TTS path was
  proven. `BEST_EXISTING_TTS_PATH=browser speechSynthesis for current UI;
  local say for local-only experiments`.

`TTS_STATUS=CONFIGURED_NOT_PROVEN beyond browser path`; a natural female voice
requires a separately authorized, benchmarked engine and voice/license decision.

### STT

`whisper.cpp` binary and `ggml-base.en.bin` are present in the repository;
the local adapter is implemented and offline. The current Admin microphone
feature remains browser SpeechRecognition, with human audio input unproven.
`STT_STATUS=INSTALLED_NOT_ACTIVE for whisper.cpp; browser SpeechRecognition is
the current UI path`.

## Image and video forensic audit

### Image

No current callable image-generation provider was proven. Repository evidence
shows a provider-neutral Creative GPU/Modal adapter and Hermes image-generation
helpers, while ComfyUI is explicitly a candidate and not installed/configured.
Existing PNGs include Admin references/artifacts and Creative scene outputs, but
their generating provider is not reliably attributable from the artifact alone.

`IMAGE_GENERATION_STATUS=CONFIGURED_NOT_PROVEN`

`IMAGE_PIPELINES_FOUND=provider-neutral Creative GPU/Modal adapter (partial,
not provider-certified); Hermes image helpers (historical/config-dependent);
ComfyUI candidate (not installed); deterministic PNG/scene generation (proven
local artifact path, not AI image generation)`.

### Video

The proven local media path is deterministic composition: FFmpeg is installed
and prior MP4/SRT/AIFF/PNG artifacts exist under
`reports/rebuild/commercial_engine_r2_assets/`. The repository also contains an
isolated Remotion 4.0.503 pilot. The report evidence identifies the narration
artifact and composition, but does not prove which AI image/video generator
created every source image.

`VIDEO_GENERATION_STATUS=PARTIAL`: `VIDEO_PIPELINES_FOUND=FFmpeg compositor
(PASS_REAL), isolated Remotion pilot (CONFIGURED_NOT_PROVEN), optional Hermes /
hosted image-video adapters (not proven callable), no certified text-to-video,
image-to-video, avatar, or lip-sync engine`.

This is consistent with the prior creative audit: no blind ComfyUI install,
unlicensed avatar weights, or unattended hosted browser provider was adopted.

## Tool calling and capability truth

The current Admin runtime has model-catalog support for `tools` and structured
outputs, but its active capability truth correctly reports Nexus MCP, Google MCP,
Gmail, Calendar, and Drive as unavailable to the direct Admin runtime unless a
separate live proof changes that state. Hermes shadow code contains MCP/tool
surfaces, but that is not evidence for Admin availability.

`TOOL_CALLING_STATUS=MODEL_SUPPORT_PRESENT; ADMIN_TOOL_SURFACE_NOT_ACTIVE`

Capability claims must be based on active runtime probes, not installation,
historical reports, or Hermes configuration. A future reliability test should
measure valid tool selection, argument schema validity, unavailable-tool honesty,
and structured-result parsing on the same model fixture.

## Task-to-capability matrix

| Task | Preferred class | Current available | Free option | Cheap paid | Premium escalation |
|---|---|---|---|---|---|
| Nova chat | cheap reliable multimodal | gpt-4o-mini | listed free model, unproven | gpt-4o-mini | Gemini Pro / approved frontier |
| Nova tool routing | structured/tool-capable | gpt-4o-mini catalog support; Admin tools unavailable | free tool-capable candidate, unproven | gpt-4o-mini | reasoning model after tool failure |
| Research extraction | deterministic + cheap model | gpt-4o-mini | free candidate | Gemini Flash | Gemini Pro |
| Research synthesis | normal multimodal | gpt-4o-mini / Flash candidates | free candidate | Gemini Flash | Gemini Pro |
| Alpha challenge | reasoning | not separately proven | free reasoning candidate | DeepSeek Flash/Pro | Gemini Pro/frontier |
| Classification | deterministic first | local Python + gpt-4o-mini fallback | local/free | gpt-4o-mini | none normally |
| Coding | coding executor + model | Codex CLI executor; model route variable | local/small model if proven | approved coding model | premium coding route |
| Repo/long-context analysis | retrieval first | local search + gpt-4o-mini | long-context free candidate | Gemini Flash | Gemini Pro |
| Image understanding | multimodal | gpt-4o-mini catalog | free multimodal candidate | Gemini Flash | Gemini Pro |
| Image generation | approved hosted/local image engine | none certified | none certified | future approved adapter | approval-gated premium provider |
| Video generation | deterministic compositor first | FFmpeg; Remotion pilot | local composition | future hosted adapter | approval-gated video provider |
| TTS | browser/local | SpeechSynthesis, `say` | browser/local | none configured | approved hosted TTS |
| Speech transcription | local/private | whisper.cpp files + browser STT | local whisper if health proven | none configured | approved transcription API |

## Proposed Resource Governor inputs

Route on `TASK_COMPLEXITY`, `EVIDENCE_UNCERTAINTY`, `COST_OF_ERROR`,
`BUSINESS_VALUE`, `TOOL_REQUIREMENT`, `LATENCY_REQUIREMENT`, `PRIVACY`,
`CONTEXT_SIZE`, and `MEDIA_TYPE`.

- `TIER_0`: deterministic code, retrieval, local FFmpeg, local whisper when
  healthy, local classification, cached facts.
- `TIER_1`: free or very-cheap model for extraction, routine summaries, low-risk
  drafts; only after availability and tool-truth tests.
- `TIER_2`: current gpt-4o-mini / approved normal model for Nova and ordinary
  governed work.
- `TIER_3`: premium long-context/reasoning/multimodal route only for high value,
  high uncertainty, difficult review, or failed lower-tier evidence.

Proposed fallback: `deterministic/local → proven free → gpt-4o-mini or approved
cheap paid → normal multimodal/reasoning → premium`, with bounded retry and no
silent capability escalation. Keep executor and model independent.

## Cost model (illustrative, not a bill)

Using the current catalog price and the observed short-call envelope, a normal
Nova turn is approximately fractions of a cent. The following Founder Mode
planning estimates assume gpt-4o-mini for ordinary text, deterministic work
first, and no paid image/video subscription:

| Profile | Assumption | Nova | Research | Alpha | Coding | Media/voice | Total planning range |
|---|---|---:|---:|---:|---:|---:|---:|
| LOW | 300 Nova turns/month, bounded research | $0.02–$0.10 | $0–$1 | $0–$1 | $0–$5 | $0–$5 | **$0–$12** |
| NORMAL | 1,000 turns, recurring research/review, some coding | $0.10–$1 | $1–$8 | $1–$8 | $5–$30 | $0–$15 | **$7–$62** |
| HEAVY | 3,000 turns, long context, frequent coding/research | $1–$8 | $5–$35 | $5–$35 | $20–$100 | $0–$75 | **$31–$253** |

These ranges deliberately exclude a future hosted image/video/avatar subscription
and premium model overuse. Actual spend depends mainly on context length, output
length, retries, premium escalation, and media provider pricing. OpenAI pricing
references are maintained separately at the [official API pricing page](https://openai.com/api/pricing/).

## Privacy boundaries

- Public research: approved external models may be used after provenance and
  terms checks.
- Internal code/architecture: use approved provider or local/private route;
  avoid sending secrets, credentials, or unreviewed proprietary material.
- Client PII, credit reports, financial data, and private documents: do not send
  to public research/free models without an approved safe path, redaction, and
  policy gate.
- Media providers may retain prompts/assets; treat hosted generation as an
  external data boundary and review license/retention/likeness terms.

## Token waste opportunities (not changed in this audit)

1. Use deterministic question classification and retrieval before an LLM.
2. Avoid repeating giant static context; send compact current state plus relevant
   retrieval only.
3. Deduplicate conversation/history and retrieval excerpts.
4. Use structured extraction models or code for simple schema work.
5. Bound retries and record provider usage so transient failures do not multiply
   cost.
6. Reserve premium reasoning and multimodal routes for measurable escalation.
7. Cache immutable repository facts and canonical capability projections with
   freshness metadata.

## Evidence ledger

- `PASS_REAL`: launchd-backed OpenRouter Nova request; OpenRouter catalog query;
  five bounded benchmark calls; FFmpeg installed; Whisper binary/model present;
  existing persisted media artifacts.
- `CONFIGURED_NOT_PROVEN`: Oracle Ollama route; Remotion pilot; Creative GPU
  adapter; local TTS handlers; model-catalog tool/vision support as an Admin
  runtime feature.
- `INSTALLED_NOT_ACTIVE`: Ollama local runtime; Whisper as current Admin STT;
  OpenCode/Kilo/Mimo executables without completed auth/model probes.
- `HISTORICAL_ONLY`: Hermes Agent as Admin route; prior provider/media reports
  without current callable proof.
- `DOCUMENTED_ONLY`: candidate ComfyUI, Wan/avatar/hosted image-video routes.
- `UNAVAILABLE/UNKNOWN`: direct OpenAI/Groq/Anthropic/Gemini Admin routes,
  approved Nous/Hermes free model, certified AI image/video generator.

## Final audit fields

`PROVIDERS_FOUND=OpenRouter, OpenAI, Groq, Anthropic, Gemini, Oracle Ollama,
local Ollama, Oracle Hermes, candidate custom/Kaggle`

`ACTIVE_PROVIDER=OpenRouter`

`ACTIVE_NOVA_MODEL=openai/gpt-4o-mini`

`FREE_MODELS_AVAILABLE=OpenRouter catalog lists free candidates; no Nexus free
model is production-proven`

`NOUS_HERMES_FREE_STATUS=NOT_PROVEN`

`CODING_EXECUTORS_AVAILABLE=Codex CLI PASS_REAL; OpenCode/Kilo/Mimo installed
but auth/model paths not proven`

`LOCAL_MODEL_STATUS=Ollama installed but inactive/unhealthy in this probe;
Oracle gemma3:4b route auth-failed in recorded health`

`IMAGE_GENERATION_STATUS=CONFIGURED_NOT_PROVEN`

`IMAGE_PIPELINES_FOUND=Creative GPU/Modal adapter, Hermes helpers, ComfyUI
candidate, deterministic local scene/PNG path`

`VIDEO_GENERATION_STATUS=PARTIAL`

`VIDEO_PIPELINES_FOUND=FFmpeg PASS_REAL, Remotion pilot, optional unproven
hosted/Hermes adapters`

`TTS_STATUS=browser path available; higher-quality hosted/local engines not
configured/proven`

`BEST_EXISTING_TTS_PATH=browser SpeechSynthesis for Admin; macOS say for local-only`

`STT_STATUS=whisper.cpp installed with model; not current Admin route; browser
SpeechRecognition remains UI path`

`TOOL_CALLING_STATUS=model support listed; Admin MCP tool execution not active`

`CURRENT_NOVA_ESTIMATED_COST=$0.15/M input + $0.60/M output; observed short
sample $0.000027–$0.000063/call`

`FOUNDER_MODE_LOW_ESTIMATE=$0–$12/month`

`FOUNDER_MODE_NORMAL_ESTIMATE=$7–$62/month`

`FOUNDER_MODE_HEAVY_ESTIMATE=$31–$253/month, excluding future media subscriptions`

`TOKEN_WASTE_OPPORTUNITIES=giant/repeated context, duplicate retrieval/history,
LLM classification/extraction, unbounded retries, premature premium routing`

`PROPOSED_TIER_0=deterministic/local`

`PROPOSED_TIER_1=proven free/very-cheap`

`PROPOSED_TIER_2=current normal operating model`

`PROPOSED_TIER_3=premium escalation`

`PROPOSED_FALLBACK_CHAIN=deterministic/local → proven free → cheap paid/current
Nova → normal reasoning/multimodal → premium`

`RESOURCE_GOVERNOR_READY_TO_DESIGN=YES`

`FILES_CHANGED=reports/architecture/NEXUS_MODEL_PROVIDER_MEDIA_CAPABILITY_AUDIT_2026-09-17.md`

`TESTS_RUN=runtime/config inventory; OpenRouter catalog query; launchd-backed
provider probe evidence; five-call bounded benchmark; local binary/model
checks; media/report forensic search`

`COMMITS=PENDING`

`RAY_ACTION_REQUIRED=NO for this audit`

`RAY_DECISION_REQUIRED=YES before enrolling a new paid provider, free model,
hosted image/video service, or premium voice`

`NEXT_MACHINE_ACTION=run the full labeled A–H benchmark across only approved
candidate models, then design the Resource Governor from measured quality/cost
and verified privacy boundaries`
