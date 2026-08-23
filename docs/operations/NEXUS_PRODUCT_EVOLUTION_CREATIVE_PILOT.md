# Product Evolution Pilot: Creative Studio

Status: `PARTIAL` pending Ray's subjective visual review and canonical output
data wiring for production concept assets.

## Contract

Outcome: Studio becomes an interactive creative workspace rather than a list
of output cards. Ray can view at least three concept territories, select one,
compare territories, view a critique, create a variation, and hand off to Ray
Review without creating a parallel Creative backend.

## Research and decision

The pilot evaluated assistant-ui, AG-UI, CopilotKit, Puck, Onlook, tldraw,
and browser-use/browsercode. Existing React and Creative Intelligence
integration are retained. A custom additive workspace was selected for this
pilot because it has the smallest dependency and migration surface: it uses
controlled React presentation, explicit sample-state labeling, and existing
callbacks for Ask Nexus/Ray Review.

Candidate disposition:

| Candidate | License / fit | Decision |
|---|---|---|
| assistant-ui | MIT; strong thread/composer primitives; duplicates current governed adapters | ADAPT later |
| AG-UI | MIT event protocol; useful for future streamed artifacts/HITL | WATCH |
| CopilotKit | useful React agent UI patterns; adds runtime/protocol coupling | WATCH |
| Puck | MIT visual React editor; useful for controlled composition | PILOT later |
| Onlook | Apache-2.0; broad visual editing surface and migration risk | WATCH |
| tldraw SDK | production use requires trial/commercial/hobby license | REJECT for this phase |
| browser-use/browsercode | MIT, but broad browser automation/security surface | REJECT for product UI |

The current pilot deliberately adopts none of these dependencies. The custom
workspace is reversible and can later host a licensed/editor capability after
an isolated pilot, security review, and approval.

## Workspace behavior

`src/components/NexusCreativeStudioWorkspace.jsx` presents three sample
territories with visual previews, audience/message/CTA, compare mode, inline
critique, variation staging, selection, canonical Creative Intelligence status,
Ask Nexus, and Ray Review handoff. Values are explicitly `SAMPLE`, `UNKNOWN`,
or `Review pending`; no business metrics or scores are fabricated. The
canonical Creative Intelligence service remains authoritative for novelty,
diversity, and similarity.

## Critic result

The pilot passes the “not dashboard-only” criterion and the interaction
acceptance contract. It remains a product pilot rather than final Creative
certification because real canonical concept/artifact fixtures and Ray's
visual judgment are required before claiming production readiness.

