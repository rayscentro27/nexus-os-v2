# Nexus Experience 2.0

## Purpose

Experience 2.0 is a presentation and navigation layer over the certified Nexus engines. It does not create new schedulers, operators, brains, approval stores, revenue stores, client stores, or voice authority.

## Route map

### Admin

`/admin` is the authenticated Admin shell. Its Command Center is the front door; hash navigation retains the existing deep links for Hermes, Nova, Alpha, Mission Control, Ray Review, Business, Creative, Operations, and System surfaces.

The actual Hermes conversation render tree remains:

`HermesWorkroom → SpecialistWorkroom → HermesChatPanel`

`HermesChatPanel` is the canonical typed and voice transcript send path.

### Client

`/client-v2/*` is the mobile-first guided funding-readiness experience. Production `/client/*` routes now enter the same V2 shell; supported legacy deep links are mapped through the existing route map. Explicit login, onboarding, and preview routes remain separate, and the legacy components remain available for rollback.

## Canonical data sources

| Surface | Source of truth |
| --- | --- |
| Command / priorities | Executive Command Center adapter and Hermes Operating Context |
| System health | Mission Control / capability health adapters |
| Approvals | Ray Review / approval queue adapters |
| Revenue | Revenue Truth Hub adapters |
| Opportunities and growth | Existing Opportunity Engine and Growth Operations surfaces |
| Creative | Creative Studio and Creative Intelligence artifacts |
| Research | Alpha research/evidence surfaces |
| Nova | Existing Nova graph and certified Telegram runtime; Admin browser adapter uses a channel-scoped Nova memory namespace |
| Client readiness | Existing client workflow, Supabase-scoped client data, readiness model |
| Documents | Supabase Storage `client-documents` plus client-scoped metadata |

Unknown, unavailable, deferred, and pending states remain explicit. UI code must not replace an unavailable source with zero or a fabricated healthy state.

## Design system

Admin continues using the existing Nexus operating CSS and Lucide React. Client V2 continues using the existing V2 Tailwind output and theme. No second UI framework was introduced. Safe reusable behavior added in this phase includes the allow-listed `SafeMarkdown` renderer and review-gated voice composer states.

## Agent separation

- Hermes remains the operator/COO conversation and canonical operating-context route.
- Nova remains a separate strategic adviser. The Admin workspace exposes its certified Telegram boundary truthfully and does not create a duplicate browser brain.
- Alpha remains the research/evidence workspace and does not receive raw client PII.

## Voice UX

The certified final-file path remains: browser MediaRecorder → Cloudflare Access → tunnel → Mac localhost → bounded WebM normalization → local whisper.cpp. The composer now holds the final transcript in a review state. Ray can edit, retry, or explicitly send; the transcript does not enter Hermes on release.

The local service preserves the final-file route and adds a bounded cumulative WebM preview route. The browser sends snapshots no faster than the MediaRecorder cadence, the server permits one active preview with a bounded per-session request count, normalizes each snapshot to WAV, and runs local whisper.cpp. Preview text is advisory; release always runs the authoritative final route and Ray must review/edit/send explicitly. Preview failures fall back to the certified final-file path. No browser cloud speech provider was introduced and raw audio remains non-retained.

The installed whisper.cpp runtime is version 1.9.1 and has no `whisper-stream` binary. Cumulative snapshots were selected as the smallest compatible private mechanism. The preview endpoint is exposed only through the existing healthy Cloudflare tunnel, with `nova.goclearonline.cc` separately protected by a Ray-only Access application. The Mac services remain bound to `127.0.0.1`.

## Client journey

The V2 client journey is: Credit Review → Credit Improvement → Business Foundation → Funding Readiness → Funding Access. Inline upload affordances now appear in the credit, business foundation, funding readiness, and central documents surfaces while preserving the existing tenant-scoped Supabase upload adapter.

Client-facing guidance remains the approved client boundary. Internal Hermes, Nova, Alpha, raw reports, and internal operating data are not exposed to clients.

## Legacy migration map

| Legacy path | Disposition |
| --- | --- |
| `/client/*` deep links | Keep during migration; map supported journey routes to V2 |
| `/client-v2/*` | Canonical client experience |
| Admin hash pages | Keep as compatibility routes; Command is the landing surface |
| Generic Hermes launcher/drawer | Keep as global access point; same Hermes engine |
| Hermes Workroom | Canonical conversation surface |
| Nova Telegram | Keep and preserve certification; no duplicate consumer |
| Nova Admin placeholder | Replaced in place with a bounded Admin-only adapter to `get_nova_graph()`; no second graph |
| Report markdown viewer | Keep, now uses safe allow-listed renderer |

No legacy component was deleted before browser cutover evidence.

## Security and authority

No `VITE_*` secret is introduced; the only new browser value is the public `VITE_NEXUS_NOVA_ENDPOINT` URL. Cloudflare, Telegram, OpenRouter, and local voice credentials remain server/runtime-only. The Nova browser adapter rejects client-sensitive identifiers, accepts bounded strategic messages, and returns advice with `execution_authority=NONE`. Existing approval gates for publishing, sending, charging, funding applications, and trading remain unchanged. Voice is input only and gained no execution authority.

## Deployment and known limitations

Build and focused tests must pass before production deployment. Existing synthetic client browser evidence covers first-login onboarding, V2 journey routes, inline upload locations, and 375/390/tablet/desktop overflow checks. Local Nova graph and public Access boundary checks pass; the final browser Nova conversation still requires Ray's authenticated Access session. The final live microphone test remains a human gate because browser microphone behavior cannot be certified from synthetic HTTP alone. TTS, WebRTC, realtime conversation, and avatars remain out of scope.

## Future hooks

The voice composer has explicit `REQUESTING_PERMISSION`, `LISTENING`, `LIVE_PREVIEW`, `FINALIZING`, `TRANSCRIPT_READY`, `EDITING`, `SENDING`, `DONE`, and `ERROR` semantics. Future TTS/avatar work must remain a separate approved phase.
