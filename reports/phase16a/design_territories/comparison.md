# GoClear Design Territories — Research-Informed Comparison

`DESIGN_DIRECTION = MANUAL_APPROVAL_REQUIRED`

These are isolated visual options for Ray. None is connected to production client routing, Supabase, Stripe, or the live portal. All three use the same safety contract: a clean client sees no score, document count, recommendation, task history, CRJ case, payment state, or synthetic journey result until real records exist.

## Research-to-experience map

| Research pattern | Exact current UX problem addressed | Applied in all three previews |
|---|---|---|
| `premium_quality_benchmark` — `reports/client_portal/client_portal_design_quality_audit.md` | A placeholder-feeling portal weakens trust before a client shares sensitive financial documents. | Intentional typography, restrained hierarchy, clear CTA, trust language, and a premium first screen. |
| `progressive_disclosure` — `reports/nexus-3/NEXUS_3_DESIGN_SYSTEM.md` | Showing every capability at first login overwhelms a new client. | Only Account Setup, the current action, Credit Review waiting state, and the next relevant document step are visible. Later stages are quiet/locked. |
| `guided_next_action` — `reports/client_portal/client_portal_design_quality_audit.md` | New clients do not know what to do next. | One dominant profile/upload CTA with a plain-language explanation of why it matters. |
| `mobile_first_client_surface` — `reports/nexus-3/NEXUS_3_DESIGN_SYSTEM.md` | A desktop-first portal can fail during the real first experience on a phone. | Stacked mobile layouts, readable upload states, preserved CTA prominence, and scrollable stage rails where necessary. |
| `real_data_badge_and_empty_state` — `reports/runtime/global_blocker_resolution_matrix_latest.json` | Demo fixtures can be mistaken for real client progress. | Explicit “not started,” “no documents yet,” and “no score exists” states; no fabricated metrics. |
| `shared_project_brain` — `reports/hermes_modernization/phase15c_final_certification.md` | Separate interfaces can explain contradictory state. | Hermes is shown as a client-safe interpreter of the same current journey state, not as an admin console. |
| `creator_critic_visual_qa` — `reports/nexus-3/NEXUS_3_CREDIT_VISUAL_FIDELITY.md` | Build success is not visual certification. | Each territory was rendered at desktop/mobile sizes, critiqued, revised once, and re-rendered. |

The requested Orca, T3 Code, Penpot, Excalidraw, and Granular references remain `PILOT_LATER` in the library because no canonical local research artifact or proven capability gap justified installing them. No vendor UI was copied.

## Territory A — Premium Financial Concierge

### Product experience

A private advisory dossier. The client feels they have entered a calm, high-touch financial review rather than an application dashboard. Serif typography, navy, warm stone, quiet borders, and a “review dossier” make the service feel considered and confidential.

### Pattern application

- Confirmation email: presented as a private invitation with a calm subject/body and one “Confirm my account” CTA.
- First-time onboarding: a concierge-style welcome followed by a short “Complete profile” action; later stages appear as quiet dossier rows rather than active feature cards.
- Clean dashboard: “Your first review” contains only what happens now, what stays private, and where to get help.
- Document upload: a restrained “Ready when you are” document-vault treatment, with format/security context and no fake count.
- Credit-review waiting: a navy assurance panel explicitly says review begins after a real report arrives.
- Journey/progress: five numbered dossier rows with Current / Next / Later language.
- Hermes: a private GoClear guide placed after the operational content, with client-safe wording.
- Mobile: hero and dossier stack; cards become a single calm reading sequence; upload CTA remains visible.

### Strongest advantage

Highest trust and strongest premium-service signal before a client shares sensitive information.

### Biggest tradeoff

The formal serif/private-dossier language may feel slower or less energetic for clients who need momentum.

### Fit and use cases

Fits a high-touch $97 readiness review, sensitive credit-document intake, advisor-led review, and clients who need confidence before action. Less suited to a highly self-serve, gamified onboarding motion.

## Territory B — Modern Guided Journey

### Product experience

A warm, momentum-oriented guided path. The client sees a clear current step, a visible five-stage rail, a clean empty state, and an approachable Hermes coach. It behaves like a guided service journey rather than a generic SaaS CRM because later capabilities remain locked until relevant evidence exists.

### Pattern application

- Confirmation email: concise, friendly, and action-led; confirmation directly opens the guided setup.
- First-time onboarding: a welcome panel and one “Start setup” CTA establish momentum immediately.
- Clean dashboard: a large first-step card states that this is a clean account with no score, history, or recommendation.
- Document upload: a visible dashed upload zone makes the next client action obvious while stating that Credit Review waits for a real document.
- Credit-review waiting: a small amber state marker communicates “waiting,” not failure or hidden work.
- Journey/progress: a five-card stage rail shows current, unlocks next, and upcoming; no later content is exposed prematurely.
- Hermes: a side panel makes conversational help discoverable without dominating the workflow.
- Mobile: cards stack; the stage rail becomes horizontally scrollable with snap-aligned steps; CTAs remain thumb-friendly.

### Strongest advantage

Best immediate clarity and momentum for a new client who needs to know exactly what to do next.

### Biggest tradeoff

The bright gradient, rounded cards, and stage rail can feel more app-like and less bespoke than a concierge service.

### Fit and use cases

Fits first-time clients, mobile-heavy onboarding, guided profile completion, upload conversion, and a service that wants to reduce hesitation. Less suited to a deliberately quiet wealth-advisory tone.

## Territory C — Editorial High-Trust Advisory

### Product experience

A reading-led advisory memo. The client encounters GoClear as an expert service that explains decisions and evidence in plain language. Green accents, editorial serif headlines, ruled sections, and “current state / what comes next” blocks create authority without dashboard density.

### Pattern application

- Confirmation email: reads like a considered welcome note and explains what happens after confirmation.
- First-time onboarding: one editorial “01 Complete your profile” action avoids form-heavy intimidation.
- Clean dashboard: current state and what comes next are separated like a short advisory memo; absent evidence is stated plainly.
- Document upload: a bordered document step gives the upload a clear place without making it feel like a file-management console.
- Credit-review waiting: a green evidence-forward waiting section explains why no result exists yet.
- Journey/progress: a ruled timeline makes sequence visible while keeping future stages informational rather than clickable features.
- Hermes: treated as an advisor’s margin note—available for interpretation, not a chat widget competing with the primary action.
- Mobile: the memo becomes a single vertical reading flow; the timeline scrolls horizontally rather than collapsing into unreadable text.

### Strongest advantage

Strongest explanation, authority, and trust for clients who want to understand why each step exists.

### Biggest tradeoff

The reading pace may make the experience feel less immediately transactional, especially for a client who only wants to upload and proceed.

### Fit and use cases

Fits credit-review education, evidence explanation, advisory reports, higher-consideration services, and clients who need rationale before sharing documents. Less suited to rapid, checklist-driven conversion.

## Visual critic pass and revision log

The critic reviewed hierarchy, typography, spacing, imagery, trust, simplicity, memorability, mobile usability, and CTA clarity at 1440px desktop and 390px mobile.

| Territory | Critic findings | Revision made | Result |
|---|---|---|---|
| A | Strongest trust and hierarchy. On mobile, the “Account setup · not started” label competed horizontally with “Your first review.” | Stacked the section heading and state label below 720px. | Cleaner mobile hierarchy without weakening the concierge tone. |
| B | Strong CTA and empty-state clarity. The five-stage rail needed an explicit mobile overflow behavior rather than appearing clipped. | Added horizontal overflow, snap alignment, padding, and preserved minimum step width. | Mobile progression remains legible while signaling additional stages. |
| C | Strongest authority and simplicity. The five-stage timeline could become cramped on narrow screens. | Added horizontal overflow, snap alignment, and fixed mobile stage widths. | The editorial sequence remains readable without turning into a dense list. |

### Imagery decision

No stock or generated imagery was added. The research supports premium hierarchy, trust, and progressive disclosure, but the first-run financial workflow does not need decorative imagery to solve its measured problems. Avoiding ornamental imagery keeps the clean empty state honest and reduces distraction from the one required action.

## Visual proof

Each territory has isolated desktop and mobile screenshots after the critic revision:

- Territory A: `territory_a/desktop.png`, `territory_a/mobile.png`
- Territory B: `territory_b/desktop.png`, `territory_b/mobile.png`
- Territory C: `territory_c/desktop.png`, `territory_c/mobile.png`

No winner is selected in this pass. Ray approval remains required before any subjective direction is connected to production client routes.
