# Approved GoClear Hybrid Direction

Status: **APPROVED BY RAY — DOCUMENTATION BASELINE**

Primary direction: **Territory B — Modern Guided Journey**

Secondary influences: **Territory A — Premium Financial Concierge** and **Territory C — Editorial High-Trust Advisory**.

This brief is a future implementation contract. It does not change production routes or client-v2 code.

## Direction ownership

### Territory B controls

Territory B is the structural authority:

- onboarding sequence and first-login flow;
- one current stage and one dominant next action;
- five-stage journey/progress model;
- page sequencing and progressive disclosure;
- clear mobile-first task completion;
- visible empty and waiting states.

### Territory A contributes

- premium hierarchy and calm visual confidence;
- restrained cards, borders, and shadows;
- private-service language around financial information;
- stronger presentation for high-value review moments;
- a polished dossier/detail treatment where context matters.

### Territory C contributes

- evidence-led copy structure;
- plain-language explanations of why a step matters;
- advisory tone and reassurance;
- “current state / what comes next” content blocks;
- editorial restraint for review, education, and waiting states.

## Required additions

### Hero image

Use one purposeful hero image or art-directed illustration on the public GoClear welcome/landing surface and, only when useful, the authenticated welcome state. It must communicate clarity, forward motion, or a calm advisory relationship—not generic finance imagery, money piles, stock-market charts, or fabricated client outcomes.

Rules:

- store as an approved local asset with responsive crops and meaningful alt text;
- keep the image subordinate to the onboarding CTA;
- use a soft editorial crop or quiet human/service scene, not a noisy dashboard screenshot;
- never imply a guaranteed credit, funding, or revenue result;
- provide a no-image fallback that preserves hierarchy and contrast;
- optimize for mobile bandwidth and respect reduced-motion preferences.

### Consistent icon system

Use the existing Lucide/React icon capability as the default system. Icons are navigation and comprehension aids, not decoration.

- one stroke family, consistent stroke width, and consistent optical size;
- pair every meaningful icon with a text label or accessible name;
- use icons for journey stages, upload, secure review, help, waiting, complete, and blocked states;
- do not mix emoji, filled vendor icon sets, and hand-drawn icons in one surface;
- use color plus text/state label; never color alone;
- define a small semantic icon map before implementation.

## Experience improvements

The hybrid corrects the current GoClear weaknesses by making the next action unmistakable, keeping the first dashboard intentionally empty, giving each stage a reason and status, and adding enough premium/advisory polish to make a sensitive financial service feel credible. It retains B’s momentum without becoming a generic SaaS CRM, A’s confidence without becoming formal or slow, and C’s explanation without turning every screen into a report.

## Non-negotiable client safety rules

- First login must resolve the authenticated client’s canonical onboarding state and route incomplete clients to onboarding before dashboard access.
- A clean real client must see `NOT_STARTED` / empty states, never demo, synthetic, certification, or another client’s records.
- No fake score, document count, task history, recommendation, payment status, CRJ case, or readiness result may be shown without a real authoritative record.
- Hermes may explain the client’s current stage and next action but must not expose operator, other-client, or internal runtime data.

## Future GoClear → Credit Repair Junkies continuity

Capture the transition as a future, approval-gated experience: GoClear completes and explains the Credit Review/readiness handoff; the client sees what is being shared, why, consent/compliance status, the next expected stage, and a return path. The future CRJ state must be sourced from real lifecycle records, preserve provenance, and never imply that a vendor handoff occurred before it is actually authorized and recorded. This task does not implement that workflow.

