# Client Dashboard Layout Audit

**Date:** 2026-07-07
**Starting commit:** ffb7da5

## Current Layout Structure

The dashboard is a 3-column grid: Sidebar (240px) | Main Content | Hermes Panel (320px).

## Why the Page Is Too Tall

The dashboard stacks **8 large sections** vertically:

1. `ClientPageHeader` — 24px padding, 20px margin-bottom
2. Hero CTA card — 20px padding, 20px margin-bottom
3. Funding Journey — 4-column grid, 20px margin-bottom
4. Estimated Funding Range — full-width card, 20px margin-bottom
5. Business Opportunities — 3-column grid, 20px margin-bottom
6. Metric grid (5 cards) — 16px gap, 20px margin-bottom
7. Dashboard grid (2 columns) — 16px gap, 20px margin-bottom
8. ClientGuidePanel — bottom of page

Total vertical content: ~2000px+ on desktop.

## Spacing Problems

| Element | Current Value | Problem |
|---------|--------------|---------|
| Main content padding | 24px 28px | Too generous for overview |
| Page header padding | 24px 28px | Oversized for dashboard |
| Page header margin-bottom | 20px | Too much |
| Card padding | 20px | Could be tighter |
| Section margin-bottom | 20px (each) | 8 sections × 20px = 160px wasted |
| Metric grid gap | 16px | Acceptable |
| Funding journey gap | 12px | Acceptable |
| Sidebar width | 240px | Could be narrower |
| Hermes panel width | 320px | Could be narrower |

## Sidebar Impact

Sidebar (240px) + Hermes (320px) = 560px of side panels. On a 1440px screen, main content gets only ~880px. On 1280px, it's ~720px. The side panels consume 39% of horizontal space.

## Components Oversized

- `ClientPageHeader` — large title (28px), generous padding
- Hero CTA — full-width card with 48px icon, generous spacing
- Funding Journey — 4-column grid with 40px icons
- Estimated Funding Range — large $25K-$80K text (32px)
- Business Opportunities — 3 cards with 100px image areas

## Fix Strategy

1. Reduce main content padding (24px 28px → 16px 20px)
2. Compress page header (24px 28px → 14px 20px, h1 28px → 20px)
3. Reduce section margins (20px → 12px)
4. Make cards tighter (20px padding → 14px)
5. Shrink sidebar (240px → 200px) and Hermes panel (320px → 280px)
6. Restructure dashboard into compact 2-column layout
7. Move metric grid + dashboard grid into tighter arrangement
8. Keep all content but compress presentation
