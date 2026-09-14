# Nexus Creative capability audit and design governance

Status: Creative review package. This document is a design intake and governance contract; it is not an Admin implementation.

## Authority

- `CODEX_CAN_CREATE_VISUAL_DESIGN=NO`
- `CODEX_CAN_IMPLEMENT_APPROVED_DESIGN=YES`
- `MAJOR_UI_CHANGE_REQUIRES_CREATIVE_DESIGN=YES`
- `MAJOR_UI_CHANGE_REQUIRES_RAY_APPROVAL=YES`
- `APPROVED_DESIGN_IS_SOURCE_OF_TRUTH=YES`

Codex may implement an approved artifact, wire data, fix functional/accessibility/responsive defects, test, build, and deploy. Codex may not invent layout, branding, graphics, visual hierarchy, or replacement assets during implementation.

## Existing capability evidence

| Capability | State | Evidence |
| --- | --- | --- |
| Web/UI design | `PARTIAL_REAL` | Existing Experience 2 design system, Admin IA, design packets, references, and Creative handlers exist; no verified human-owned Figma product file is connected. |
| Branding | `PASS_REAL` | GoClear/Nexus SVG marks and a documented token system exist in `public/brand/` and `docs/experience-2/DESIGN_SYSTEM.md`. |
| Graphics | `PASS_REAL` | Creative library, campaign graphics, posters, thumbnails, and video assets exist under `public/creative-*` and `public/creative-library/`. |
| Figma | `MISSING` | No repository or connected Figma design source was found. |
| Canva | `PARTIAL_REAL` | Canva designs are discoverable/editable through the connected workspace; no suitable Admin template was found in the audit. |
| Landing pages | `PASS_REAL` | Existing GoClear public routes and campaign assets are present. |
| Design QA | `PARTIAL_REAL` | Deterministic `review_ui_quality.py` exists; human visual approval and deployed comparison remain required. |
| Remote design worker | `MISSING` | No verified remote design worker with an approved handoff contract was found. |

## Surface ownership

| Surface | Preferred owner/tool | Codex handoff |
| --- | --- | --- |
| Product UI | Creative + Figma | Figma frames, components, tokens, responsive states, annotations, approved export/reference. |
| Landing page | Creative + OpenPage for bounded prototypes; existing Nexus stack for production | Structured page brief, approved visual artifact, copy/CTA contract, assets. |
| Marketing site | Creative + existing Nexus stack; HugoBlox only for a separate content-site decision | IA, theme, content model, SEO/analytics requirements, approved screens. |
| Visual asset | Creative + Canva and existing asset library | Asset IDs/paths, crop rules, alt text, license/provenance, placement specs. |
| Design QA | Creative + Impeccable critique + browser screenshots | Findings classified as implementation defect, design revision, or Ray decision. |

## Tool selection

| Tool | Recommended role | Decision |
| --- | --- | --- |
| Figma | Product UI, Admin, Client Portal, workflows | Recommended primary product-design authority. Dev Mode exposes specs, components, variables, and code-facing context. |
| Canva | Brand assets, campaign graphics, social, hero artwork, collateral | Recommended marketing graphics lane; not the primary product-UI source of truth. |
| Impeccable | Critique and anti-pattern QA | Recommended as critique only. It reviews without changing the design; Ray/Creative decides. |
| Onlook | Optional visual editing for isolated React experiments | Compatible with React/Vite according to its current React page, but not recommended for Admin until a controlled canary proves source diffs and design governance. |
| OpenPage | Self-hosted JSON-first landing-page prototyping/factory | Research candidate for campaign/landing prototypes, not Admin or Client Portal replacement. |
| HugoBlox | Separate content/SEO/marketing-site reference or pilot | Not a production dependency for the current Nexus app; evaluate only for a distinct content site. |
| Layout | Design-system extraction and structured design-to-code context | Recommended bridge after Creative approves the visual direction; it can expose tokens, typography, components, and visual patterns to an implementation agent. |

Evidence used: Figma Dev Mode ([Figma](https://www.figma.com/dev-mode/)); Canva Brand Kit ([Canva](https://www.canva.com/business/features/brand/)); Impeccable critique ([Impeccable](https://impeccable.style/docs/critique/)); Onlook React/Vite support ([Onlook](https://www.onlook.com/for/react)); OpenPage JSON-first editor ([OpenPage](https://github.com/buildingopen/openpage)); HugoBlox workflow ([HugoBlox](https://hugoblox.com/docs/guide)); Layout structured handoff ([Layout](https://layout.design/docs)).

## Design-to-Codex contract

Every approved handoff must include:

```text
DESIGN_TOKENS
SPACING
TYPOGRAPHY
COLORS
COMPONENTS
ICON_SPECS
LAYOUT_DIMENSIONS
RESPONSIVE_RULES
ASSET_REFERENCES
INTERACTION_RULES
DO_NOT_CHANGE_RULES
APPROVED_ARTIFACT_URL
RAY_APPROVAL_RECEIPT
```

The implementation gate is closed when `APPROVED_ARTIFACT_URL` or an equivalent editable artifact, `RAY_APPROVAL_RECEIPT`, and the structured contract are absent.

## Canonical workflow

```text
BUSINESS_NEED
→ CREATIVE_SURFACE_CLASSIFICATION
→ DESIGN_ARTIFACT
→ CREATIVE_CRITIQUE
→ CREATIVE_REVISION
→ RAY_APPROVAL
→ DESIGN_FREEZE
→ CODEX_IMPLEMENTATION
→ BROWSER_SCREENSHOT
→ CREATIVE_COMPARISON
→ CODEX_DEFECT_REPAIR
→ RAY_FINAL_ACCEPTANCE
→ DEPLOY
```

## Admin Command Center information architecture proposal

The current Admin Live Intelligence feedback should be addressed through five operator-facing surfaces, not one denser dashboard:

| Surface | Question answered | Primary data | Primary actions | Visualization |
| --- | --- | --- | --- | --- |
| Executive Command Center | What changed, what matters, and what happens next? | current work, meaningful changes, revenue progress, blockers, Ray decisions | open next work, inspect change, open decision | attention-ranked summary, timeline, next-action rail |
| Research Command Center | What is Research learning now? | lane, current question, sources, findings, Alpha view, next lane | inspect finding, open evidence, follow up | lane status, evidence timeline, finding list |
| Opportunity Board | Which findings could become value? | opportunities, classification, missing evidence, cheapest test | inspect, queue experiment, request Ray decision | opportunity stages and test cards |
| Department Operations | Who received work and what is moving? | departments, handoffs, work orders, receipts, blockers | open work, retry eligible work, inspect return path | department matrix and handoff timeline |
| Ray Decision Queue | What genuinely requires Ray? | evidence, risk, recommendation, GO/REWORK/HOLD/REJECT | decide or defer | decision cards with evidence and boundary |

Supporting detail views: YouTube Intelligence, SEO/Current Demand, Campaigns, and Handoffs. Summary screens link to detail; raw reports stay behind evidence drawers.

## Admin implementation handoff draft

The next Creative artifact must show a desktop Command Center state and responsive variants for:

- current operating status expressed as a reason, not only `HEALTHY`;
- “since last check” changes;
- progress toward revenue or customer impact with source context;
- stuck work and why it is stuck;
- Ray decisions with evidence and explicit boundary;
- one clearly dominant next action;
- icon and label system tied to the existing Nexus token set;
- intentional scroll behavior and compact density;
- click destinations for Work, Research, Opportunity, Department, and Ray Review.

This is a Creative brief, not a visual implementation instruction for Codex.

## Current artifact boundary

`ADMIN_DESIGN_ARTIFACT_CREATED=NO` for this run. The connected Canva workspace did not return a suitable editable Admin template and its permitted generation types rejected the requested artifact. No Codex-authored visual design was substituted. Creative must create or select the editable Figma/Canva artifact before implementation begins.

`CODEX_IMPLEMENTATION_STARTED=NO`.

