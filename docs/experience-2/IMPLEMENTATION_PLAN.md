# Nexus Experience 2.0 Implementation Plan

**This is a future cutover plan. It is not executed by the design-reset phase.**

## Stage A — New shell + Command

Build the six-item shell and Command over existing canonical read models. Keep old routes available behind a reversible flag. Gate on source truth, responsive layout, auth, and no fake metrics.

## Stage B — Work + Ray Review consolidation

Create the Work presentation model over Active Operator, work orders, Ray Review, Mission Control, reports, receipts, and approvals. Do not create a new work store. Gate on timeline/source/approval parity.

## Stage C — Universal Agent composer

Extract the shared composer contract for text, attachments, page context, voice preview, review-before-send, and safe Markdown. Preserve Hermes canonical routing and final-file Voice fallback.

## Stage D — Agent presentations

Replace the visual shells for Hermes, Nova, and Alpha while retaining their separate engines, memory scopes, transports, and authority. Add explicit handoff and context events.

## Stage E — Business + Studio

Group Clients, Credit & Funding, Revenue, Opportunities, Growth, Research, Creative, Campaigns, Artifacts, and Reports under outcome-oriented destinations. Preserve tenant boundaries and source truth.

## Stage F — System / Mission Control

Move technical observability behind System. Keep Mission Control canonical for health and capabilities. Make deferred/not-connected states prominent and honest.

## Stage G — Client Portal

Implement the guided mobile-first client journey, no-data welcome, inline uploads, central Documents library, recommendations, and tenant-isolation tests.

## Stage H — Legacy cutover/removal

After browser and human review, switch canonical routes, monitor, confirm no imports/use, then deprecate and eventually remove duplicate shells. Maintain rollback until production evidence is stable.

## Validation gates for every stage

- No production runtime or authority change outside scope.
- Existing focused tests pass; touched engine tests rerun.
- Typecheck/build pass.
- Auth, role, tenant, and secret scans pass.
- Unknown/not-connected states remain truthful.
- Desktop, tablet, and 375/390px browser checks pass where relevant.
- Human review for visual hierarchy before advancing.

## Explicit non-goals

No TTS, WebRTC, avatar, business configuration expansion, commercial packaging, TradingOps, new scheduler, parallel operator, parallel health/revenue/approval store, or agent brain merge.
