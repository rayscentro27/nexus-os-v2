# Nexus — Command Center + Source Intake Polish (report)

- generated_at: 2026-06-25 · build PASS · watch PASS

## Command Center fixes
- Uses **full desktop width** (`.main.wide`; global 1180px cap removed for this tab only).
- **3-column mission-control grid restored** (`nx-mc-grid`): col1 Hermes workspace + Source Notebook
  + Recent Outputs · col2 Jarvis + compact System Awareness · col3 Oracle + Memory Galaxy.
  Responsive: 2-col ≤1480px, 1-col ≤1024px.
- **Systems Status compacted** into a small "System Awareness" card (counts + failing jobs +
  action-capable count + `<details>` for full detail). No safety info removed.
- Fixed: blank right space, early stacking, excess scrolling, misaligned workspace, oversized block.

## Source Intake fixes
- Sidebar tab **renamed to "Source Intake & Review"** (route key `intake` kept).
- Full width; top status pills kept (Research Engine / YouTube Capture CLI / Hermes Review / Model v1).
- **Connection Status compacted** into a collapsible `<details>` card on the right rail.
- Recent Sources: filter chips (All / Needs Review / Scored / Parked), title truncation, selected-row
  highlight, more width.
- **Hermes Review panel added** to the right rail (populated on row selection).

## Row selection behavior
Clicking a row highlights it and populates the Hermes Review panel: title, source_url, captured_at,
transcript_status, review_status, rating_model_version, score (+ low/moderate/high), category,
destination, plain-English summary, why it matters, recommended next action, compliance notes, tags,
reasons (via Explain Score). Data from `research_sources` (+ `metadata`).

## Actions — live vs task_request vs disabled
- **Live (navigate/UI):** Review with Hermes (→ Command Center), Explain Score (deterministic inline).
- **task_request (sign-off only):** Create Task Request, Promote to Opportunity Lab, Send to Creative
  Studio, Mark Research Only, Park Source, Submit Source.
- **Disabled/inert:** Jarvis Open Browser/TradingView/VS Code/Run Safe Command ("Mac bridge not
  connected"); browser capture; publish/send/trade/deploy; external AI on transcript text.

## Captured records still appear
✅ `research_sources` reads show "5 Ways to Improve Your Credit Score in 30 Days…" (credit_funding →
GoClear, 29) and "Hermes SEO Agent OS…" (ai_tooling → Ops, 22). Selecting either populates Review.

## Safety
build PASS · watch PASS · Hermes modes intact · no scheduler · no v1 touched · no capture · no
publish/send/trade/deploy · approval `13eafcab` pending · FB `publish_enabled` false · no secrets ·
`.env` not committed · no schema/RLS change.

## Next build
Wire a "Run approved capture" action (task_request → worker runs the CLI wrapper) so the capture loop
closes from the UI; add real disposition/status writes (research_sources.metadata.review_status +
nexus_events proof) when Ray approves a routing action.
