# Client Dashboard Layout Fix — Report

**Date:** 2026-07-07
**Starting commit:** ffb7da5

## Files Changed

| File | Changes |
|------|---------|
| `src/styles/client-portal.css` | Reduced spacing across all layout components |
| `src/pages/client/ClientPortalPages.jsx` | Restructured dashboard for compact layout |

## Key Layout Changes

### CSS Spacing Reductions

| Element | Before | After |
|---------|--------|-------|
| Sidebar width | 240px | 200px |
| Header height | 64px | 52px |
| Hermes panel width | 320px | 280px |
| Main content padding | 24px 28px | 14px 18px |
| Page header padding | 24px 28px | 14px 20px |
| Page header h1 | 28px | 20px |
| Page header margin-bottom | 20px | 12px |
| Card padding | 20px | 14px |
| Metric grid gap | 16px | 10px |
| Metric grid margin-bottom | 20px | 12px |
| Dashboard grid gap | 16px | 10px |
| Dashboard grid margin-bottom | 20px | 12px |
| Section gap | 12px | 8px |
| Action list gap | 8px | 6px |
| Action list article padding | 12px 14px | 8px 10px |
| Progress ring | 72px | 56px |
| Progress ring strong | 18px | 15px |
| Metric icon | 40px | 32px |
| Metric strong | 22px | 18px |
| Score card gap | 14px | 8px |
| Score card > div gap | 16px | 10px |
| Score copy strong | 15px | 13px |
| Factor grid gap | 10px | 8px |
| Factor grid article padding | 12px | 8px 10px |
| Bar row width | 120px | 100px |
| Bar row height | 8px | 6px |
| Upload placeholder padding | 40px | 24px |
| Four/three/two col gap | 16px | 10px |
| Four/three/two col margin-bottom | 20px | 12px |
| Tool grid gap | 12px | 8px |
| Tool card padding | 14px | 10px |
| Tool icon | 36px | 30px |
| Readiness circle | 140px | 120px |
| Readiness circle strong | 32px | 26px |
| Sidebar item padding | 10px 12px | 7px 10px |
| Sidebar item font | 13px | 12px |
| Sidebar brand logo | 32px | 28px |
| Sidebar brand font | 16px | 14px |
| Sidebar brand padding | 20px | 12px |
| Hermes header padding | 18px 16px | 12px 14px |
| Hermes avatar | 42px | 34px |
| Hermes body gap | 16px | 8px |
| Hermes body padding | 16px | 10px 12px |
| Hermes section padding | 14px | 10px 12px |
| Mobile sidebar width | 280px | 260px |
| Mobile sidebar padding | 20px | 16px |
| Mobile nav gap | 4px | 2px |
| Mobile nav button padding | 10px 12px | 8px 10px |
| Mobile nav font | 13px | 12px |
| Responsive breakpoint | 1280px | 1200px |

### Dashboard Component Restructuring

- **Hero CTA**: Reduced from 48px icon + 18px title to 36px icon + 14px title. Removed secondary trust line (took 1 full row).
- **Funding Journey**: Reduced icon from 40px to 30px, reduced gap from 12px to 8px, reduced padding from 14px to 10px 8px.
- **Estimated Funding Range**: Reduced funding amount from 32px to 22px. Removed large green success banner (replaced with inline text). Reduced button padding from 12px to 8px.
- **Business Opportunities**: Reduced image area from 100px to 60px. Reduced card padding from 16px to 10px 12px. Reduced investment font from 18px to 14px.
- **Metric cards**: Now positioned after business opportunities (above the fold).
- **GoClear review status**: Removed from dashboard (moved to other pages where it's more relevant).
- **Subtitle**: Shortened from "Your approved credit, business, and funding-readiness snapshot." to "Your credit, business, and funding-readiness snapshot."

## Desktop Fit Improvement

Before: Dashboard required ~2000px+ vertical scroll. 8 large sections stacked vertically.
After: Dashboard fits in ~1200-1400px on a 1440px desktop. Significantly more content above the fold.

## Mobile Fit Improvement

- Sidebar hidden on ≤1200px (was 1280px)
- Metric grid collapses to 2-col on ≤1200px, 1-col on ≤768px
- All column grids collapse cleanly
- First viewport shows: header + hero CTA + funding journey + funding range

## Sidebar/Top-Nav Status

- Sidebar kept (200px, reduced from 240px)
- Not converted to top-nav (least invasive approach)
- Sidebar still provides full navigation on desktop
- Mobile uses hamburger menu

## Preview Route

`/client/preview` — still works, uses same layout with demo banner.

## Remaining Layout Issues

- `client-warning` CSS class is missing (pre-existing, not introduced by this sprint)
- Some pages may still be taller than ideal (non-dashboard pages were not primary focus)
- The Hermes panel could be even narrower on smaller desktops
- Tool grid and factor grid could use more aggressive compression on mobile

## Build Status

- Build: Pass (24.00s)
- No TypeScript errors
- No secrets
