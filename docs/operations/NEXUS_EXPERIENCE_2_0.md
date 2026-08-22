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
| Nova | Existing Nova graph and certified Telegram runtime; browser adapter is not connected |
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

The current local service exposes final-file transcription only. Progressive private partial transcript streaming is therefore not claimed as complete in this cut; no browser cloud speech provider was introduced. A future private streaming endpoint may be added without changing the final-transcript fallback contract. Raw audio remains non-retained.

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
| Report markdown viewer | Keep, now uses safe allow-listed renderer |

No legacy component was deleted before browser cutover evidence.

## Security and authority

No `VITE_*` secret is introduced. Cloudflare, Telegram, OpenRouter, and local voice credentials remain server/runtime-only. Existing approval gates for publishing, sending, charging, funding applications, and trading remain unchanged. Voice is input only and gained no execution authority.

## Deployment and known limitations

Build and focused tests must pass before production deployment. Browser certification must cover authenticated Admin and client routes at desktop and mobile widths. The current implementation is ready for a human voice UX test only after a private incremental transcript transport is available or the acceptance scope explicitly accepts the certified final-only fallback; TTS, WebRTC, realtime conversation, and avatars remain out of scope.

## Future hooks

The voice composer already has explicit `LISTENING`, `PROCESSING`, `TRANSCRIPT_READY`, `EDITING` (textarea interaction), `SENDING`, `DONE`, and `ERROR` semantics. Future private partial events can update the same draft without changing Hermes routing. TTS/avatar work must remain a separate approved phase.
