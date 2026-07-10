# Customer Flow Simplification Audit

- Current world-class design preserved: `True`
- Old design restored: `False`
- Starting baseline: `d512a04`
- Current working head before this change: `03116c6`

## Current Routes / Tabs

- Visible simplified routes: Home, Credit Profile, Business Profile, Business Funding, Documents, Resources, Request Review.
- Compatibility routes retained: `/client/credit-utilization`, `/client/credit-repair-journey`, `/client/dispute-review`, `/client/business-setup`, `/client/funding-readiness`.

## Complexity Reduced

- Credit Health, Credit Repair Journey, Dispute Review, and Credit Utilization are grouped under Credit Profile.
- Profile & Info and Business Setup are grouped under Business Profile.
- Funding Readiness and funding option review are grouped under Business Funding.
- Documents and Resources remain support routes.

## Reused Logic

- Existing world-class shell and card system.
- Inline document upload.
- Credit repair case engine and dispute options.
- DocuPost approval-gated flow.
- Client guidance and resource helpers.

## Simplification Plan Applied

- Simplified sidebar labels.
- Added three-track Home dashboard.
- Added report-first Credit Profile flow.
- Clarified Business Profile and Business Funding page intent.
- Kept deeper strategy detail in admin/specialist helpers.
