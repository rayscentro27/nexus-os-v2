# Nexus — Source Intake & Review UI

Tab `intake` renders `source-intake/SourceIntakeReviewPage.tsx`. Sidebar label is now
**"Source Intake & Review"** (route key `intake` unchanged for compatibility). The page uses full
desktop width (`.main.wide`).

## Layout (`nx-si-grid`, responsive)
- **Main column:** Add Source tiles + Source Entry form (side-by-side, wrap on narrow), then the
  full-width **Recent Sources** table.
- **Right rail:** **Hermes Review** panel (populated on row selection) + a **compact, collapsible
  Connection Status** (`<details>`).
- Top status pills: Research Engine: Partial · YouTube Capture (CLI): Approved · Hermes Review:
  Available · Rating Model v1: Active.

## Row selection → Hermes Review
Clicking a Recent Sources row highlights it and populates the Hermes Review panel with: title,
source URL, captured_at, transcript_status, review_status, rating_model_version, score (+ low/
moderate/high sense), category, destination, plain-English summary (`snippet`), why it matters,
recommended next action, compliance notes, tags, and (via "Explain Score") reasons-for / reasons-
against. Data comes from `research_sources` (incl. its `metadata` rating).

## Actions (all safe)
- **Review with Hermes** → navigates to Command Center (keeps the selected source).
- **Explain Score** → toggles deterministic reasons inline (no external AI).
- **Create Task Request / Promote to Opportunity Lab / Send to Creative Studio / Mark Research Only /
  Park Source** → file approval-gated `task_requests` (sign-off records only).
- **Submit Source** (entry form) → files a `task_request`; helper copy: "Browser capture is disabled.
  Approved capture runs through the local CLI wrapper after Ray approval."

## Never
No browser capture (no yt-dlp), no publish/send/trade/deploy, no scheduler, no external AI on
transcript text, no schema change, no RLS change.
