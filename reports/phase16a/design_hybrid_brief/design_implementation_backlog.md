# GoClear Hybrid Design Implementation Backlog

This backlog is for a later approved implementation pass. It does not claim that any item below is complete.

## P0 — Critical

| Title | Objective | Why it matters | Dependencies | Risk if skipped |
|---|---|---|---|---|
| Canonical onboarding route/gate | Route incomplete first-login clients to onboarding using authoritative intake state. | Prevents a confusing or unsafe first dashboard. | Existing auth/context and client profile schema. | New clients bypass setup or see the wrong surface. |
| Clean real-client empty-state rendering | Enforce REAL/SYNTHETIC/DEMO/CERTIFICATION boundaries in every client query and view. | Prevents fabricated progress and cross-client leakage. | Adapter/query audit and authenticated browser proof. | Trust and data-safety failure. |
| Branded Auth email templates | Configure and preview confirmation, reset, invitation, and email-change copy. | The first trust touchpoint is currently generic/unverified. | Supabase dashboard/project access and approved copy. | Clients receive an inconsistent technical experience. |
| First-run dashboard simplification | Implement the B-led current-stage/next-action structure with A/C content treatment. | Reduces overwhelm and improves completion. | Onboarding gate and clean-state contract. | Portal remains a dense generic dashboard. |

## P1 — High

| Title | Objective | Why it matters | Dependencies | Risk if skipped |
|---|---|---|---|---|
| Hero image asset system | Add an approved responsive GoClear hero asset with alt/fallback rules. | Supplies premium memorability without outcome claims. | Ray-approved asset/rights review. | Hero becomes either generic or visually inconsistent. |
| Consistent icon system integration | Map journey/status/actions to one Lucide-based icon vocabulary. | Improves scanning and reduces visual noise. | Existing icon package and semantic map. | Mixed icon language undermines polish/accessibility. |
| Progress UI pass | Extend the existing journey rail with current/upcoming/complete semantics and mobile behavior. | Makes staged service progress understandable. | Canonical journey state. | Clients cannot tell what matters now. |
| Trust copy pass | Apply C-inspired current-state, evidence, and no-guarantee copy across pages. | Explains sensitive requests and boundaries. | Product/legal copy review. | Polished UI may still feel vague or sales-led. |
| Document upload/waiting states | Align upload, processing, missing, and review states to the hybrid system. | Makes the Credit Review handoff legible. | Real document status model. | Clients may interpret waiting as failure or completed work. |

## P2 — Medium

| Title | Objective | Why it matters | Dependencies | Risk if skipped |
|---|---|---|---|---|
| Stage-filtered resources | Reveal only education relevant to the current journey stage. | Supports guidance without information overload. | Content taxonomy and stage state. | Resources become a content dump. |
| Hermes client context pass | Make Hermes answer from current client stage, missing steps, and real documents only. | Makes help useful without exposing operator data. | Governed client capability contract. | Chat becomes generic or unsafe. |
| Desktop density pass | Reduce needless scroll while preserving advisory whitespace. | Improves first-session efficiency. | Approved direction and browser visual QA. | Desktop feels either sparse or overly long. |
| Mobile upload and support QA | Certify touch targets, file selection, waiting state, and Hermes entry on narrow screens. | Many clients will begin on mobile. | Browser/device viewport proof. | First action may fail on phone. |
| Billing state language | Apply the hybrid status treatment without weakening Stripe gates. | Prevents payment ambiguity. | Existing payment gate and approved copy. | Clients may infer a charge or fulfillment that did not occur. |

## P3 — Nice-to-have

| Title | Objective | Why it matters | Dependencies | Risk if skipped |
|---|---|---|---|---|
| Editorial evidence expansions | Add optional “why this matters” and source detail sections after verified results. | Deepens trust for clients who want explanation. | Verified evidence and content review. | Lower educational depth, but no core flow loss. |
| Hero motion refinement | Add subtle reduced-motion-safe entrance treatment. | Adds polish without changing structure. | Final asset and accessibility QA. | Minimal; static hero remains valid. |
| Future CRJ transition prototype | Prototype consent, data scope, handoff, and return states without executing a vendor handoff. | Prepares continuity between GoClear and CRJ. | Approved lifecycle contract and compliance review. | Later transition may feel disconnected. |

