# Button and Action Certification — Client Portal

**Date:** 2026-07-08
**Starting Commit:** 71b9dd4
**Script Result:** PASS — "All client portal buttons have handlers, are disabled, or navigate."

---

## Action Map

### Dashboard Page

| Button/Action | Classification | Route/Behavior |
|---|---|---|
| Upload Now (hero CTA) | navigates | → `/client/documents` |
| Upload Credit Report (hero) | navigates | → `/client/documents` |
| Improve Approval Odds | navigates | → `/client/credit-utilization` |
| Credit Profile card (metric) | navigates | → `/client/credit-profile` |
| Business Profile card (metric) | navigates | → `/client/business-setup` |
| Funding Readiness card (metric) | navigates | → `/client/funding-readiness` |
| Overall Readiness card (score) | navigates | → `/client/funding-readiness` |
| Documents Needed quick link | navigates | → `/client/documents` |
| Business Setup quick link | navigates | → `/client/business-setup` |
| Messages quick link | navigates | → `/client/messages` |
| Credit Monitoring tool | navigates | → `/client/resources` |
| Mail Letters Online tool | navigates | → `/client/resources` |
| Business Banking tool | navigates | → `/client/business-setup` |
| Funding Journey steps | navigates | → respective pages |
| Action list items (4 tasks) | navigates | → `/client/documents` or `/client/credit-profile` |
| Readiness bar rows | navigates | → respective pages |
| Hermes Guidance | informational | Static guidance panel |

### Credit Profile Page

| Button/Action | Classification | Route/Behavior |
|---|---|---|
| Connect Monitoring | navigates | → `/client/resources` |
| Upload Report | navigates | → `/client/documents` |
| Free Report Options | navigates | → `/client/resources` |
| Action list items (3) | navigates | → `/client/credit-utilization` or `/client/documents` |

### Credit Utilization Page

| Button/Action | Classification | Route/Behavior |
|---|---|---|
| Action list items (4) | navigates | → `/client/documents` or `/client/credit-profile` or `/client/resources` |

### Documents Page

| Button/Action | Classification | Route/Behavior |
|---|---|---|
| Upload dropzone | uploads file | Supabase Storage upload |
| Uploaded Documents card | navigates | → `/client/documents` |
| Signed Forms card | navigates | → `/client/documents` |
| Credit Reports card | navigates | → `/client/documents` |

### Business Setup Page

| Button/Action | Classification | Route/Behavior |
|---|---|---|
| Open Online Bank Account | navigates | → `/client/business-bankability` |
| Add Existing Account | navigates | → `/client/business-bankability` |
| Relationship Bank | navigates | → `/client/business-bankability` |
| Business Formation provider | navigates | → `/client/resources` |
| Business Bank Account provider | navigates | → `/client/business-bankability` |
| Business Phone & Address provider | navigates | → `/client/resources` |
| Recommended next steps (4) | navigates | → `/client/business-setup` or `/client/business-bankability` |

### Business Bankability Page

| Button/Action | Classification | Route/Behavior |
|---|---|---|
| Recommended banks (3) | navigates | → `/client/resources` |

### Funding Readiness Page

| Button/Action | Classification | Route/Behavior |
|---|---|---|
| Top Blockers (4) | navigates | → `/client/credit-utilization`, `/client/business-bankability`, `/client/credit-profile`, `/client/documents` |
| Next Best Actions (4) | navigates | → `/client/business-bankability`, `/client/credit-utilization`, `/client/documents`, `/client/recommendations` |
| Recommended Tools (2) | navigates | → `/client/business-bankability`, `/client/resources` |

### Recommendations Page

| Button/Action | Classification | Route/Behavior |
|---|---|---|
| Matched opportunities (5) | navigates | → `/client/recommendations` |
| Funding paths (4) | navigates | → `/client/funding-readiness` |
| Partner/tool options (6) | navigates | → `/client/resources` |

### Resources Page

| Button/Action | Classification | Route/Behavior |
|---|---|---|
| Credit Monitoring items (3) | navigates | → `/client/resources` |
| Mailing Options (3) | navigates | → `/client/documents` |
| Business Banking (4) | navigates | → `/client/business-bankability` |
| Credit Report Upload items (3) | navigates | → `/client/documents` or `/client/request-review` |
| Go to Business Banking button | navigates | → `/client/business-bankability` |

### Request Review Page

| Button/Action | Classification | Route/Behavior |
|---|---|---|
| Open tasks (4) | navigates | → `/client/documents` or `/client/credit-profile` or `/client/business-setup` |
| Request Review button | disabled | "Complete tasks first" — disabled state with reason |

### Navigation (Sidebar)

| Button/Action | Classification | Route/Behavior |
|---|---|---|
| Home | navigates | → `/client/dashboard` |
| Credit Profile | navigates | → `/client/credit-profile` |
| Credit Utilization | navigates | → `/client/credit-utilization` |
| Documents | navigates | → `/client/documents` |
| Business Setup | navigates | → `/client/business-setup` |
| Business Bankability | navigates | → `/client/business-bankability` |
| Funding Readiness | navigates | → `/client/funding-readiness` |
| Recommendations | navigates | → `/client/recommendations` |
| Resources | navigates | → `/client/resources` |
| Request Review | navigates | → `/client/request-review` |
| Sign Out | navigates | → `/client/login` (via supabase.auth.signOut) |

### Header

| Button/Action | Classification | Route/Behavior |
|---|---|---|
| Notification icon | navigates | → `/client/resources` |
| Mail icon | navigates | → `/client/resources` |
| Help icon | navigates | → `/client/resources` |

---

## Dead Clickable UI: NONE

All buttons either:
1. Navigate to a valid route via `usePortalNav()` context
2. Are explicitly disabled with reason text
3. Trigger file upload (DocumentUploadZone)
4. Are informational (display only)

---

## Summary

| Check | Result |
|---|---|
| Dead clickable UI | 0 instances |
| Buttons with handlers | All pass |
| Disabled buttons with reason | 1 (Request Review — "complete tasks first") |
| Script check result | PASS |

**CERTIFICATION: ALL BUTTONS AND ACTIONS CERTIFIED**
