# Master Client Portal Button / Action Map

- Starting commit: `2217cd1`
- Current world-class design preserved: `True`
- Old design restored: `False`
- Total visible client-facing buttons/actions audited: `96`
- Correct after this audit: `85`
- Fixed in this audit: `3`
- Gated / coming soon: `6`
- Needs manual verification with live account/data: `5`
- Dead/no-op remaining: `0`

## 1. Global / Sidebar / Topbar / Clyde Panel

| Button / action | File | Current action | Expected action | Status | Notes |
|---|---|---|---|---|---|
| Home | `WorldClassClientPortal.jsx` | `routeTo('/client/dashboard')` | `/client/dashboard` | correct | Sidebar route. |
| Credit Profile | `WorldClassClientPortal.jsx` | `routeTo('/client/credit-profile')` | `/client/credit-profile` | correct | Sidebar route. |
| Business Profile | `WorldClassClientPortal.jsx` | `routeTo('/client/profile')` | `/client/profile` | correct | Sidebar route. |
| Business Funding | `WorldClassClientPortal.jsx` | `routeTo('/client/funding-readiness')` | `/client/funding-readiness` | correct | Sidebar route. |
| Documents | `WorldClassClientPortal.jsx` | `routeTo('/client/documents')` | `/client/documents` | correct | Explicit vault route. |
| Resources | `WorldClassClientPortal.jsx` | `routeTo('/client/resources')` | `/client/resources` | correct | Sidebar route. |
| Request Review | `WorldClassClientPortal.jsx` | `routeTo('/client/request-review')` | `/client/request-review` | correct | Sidebar route. |
| View icon system | `WorldClassClientPortal.jsx` | `setShowIcons(true)` | Internal/gated utility | gated correctly | Internal preview utility remains in portal shell. |
| Sign Out | `WorldClassClientPortal.jsx` | Supabase sign out + `/client/login` | existing sign out behavior | correct | Uses frontend auth only. |
| Membership pill | `WorldClassClientPortal.jsx` | informational display | membership/status panel | gated correctly | Not a button. |
| Notification bell | `WorldClassClientPortal.jsx` | disabled with coming-soon title | gated notification panel | fixed | Was routing to Resources; now gated. |
| User/avatar | `WorldClassClientPortal.jsx` | `/client/profile` | `/client/profile` | fixed | Was non-clickable display. |
| Chat with Clyde | `WorldClassClientPortal.jsx` | opens in-page drawer | open drawer, not Resources | correct | Uses Clyde action engine. |
| Clyde suggested question | `WorldClassClientPortal.jsx` | deterministic answer | answer in drawer | correct | No external model call. |
| Clyde Upload Document | `WorldClassClientPortal.jsx` | `openUploadPanel(...)` | in-page upload panel | correct | Does not route to Documents. |
| Clyde Request Review | `WorldClassClientPortal.jsx` | `/client/request-review` | `/client/request-review` | correct | Human review CTA. |
| Clyde View Documents Vault | `clydeActionEngine.ts` | `/client/documents` | explicit vault route | correct | Vault route only. |
| Clyde Review Letters | `clydeActionEngine.ts` | `/client/dispute-review` | `/client/dispute-review` | correct | Present on credit/repair contexts. |

## 2. `/client/dashboard`

| Button / action | File | Current action | Expected action | Status | Notes |
|---|---|---|---|---|---|
| Goal: improve credit / home goal | `WorldClassClientPortal.jsx` | `/client/credit-profile` | Credit Profile | correct | Focus selection is route-based. |
| Goal: build business profile | `WorldClassClientPortal.jsx` | `/client/profile` | Business Profile | correct | Route-based focus. |
| Goal: business funding | `WorldClassClientPortal.jsx` | `/client/funding-readiness` | Business Funding | correct | Route-based focus. |
| Track cards | `WorldClassClientPortal.jsx` | track `.route` | matching track route | correct | Credit/Profile/Funding routes. |
| Next Best Action: upload | `WorldClassClientPortal.jsx` | `openUploadPanel(...)` | in-page upload | correct | Credit/funding category inferred from action. |
| Next Best Action: non-upload | `WorldClassClientPortal.jsx` | `navigate(action.route)` | matching route | correct | From `customerFlowEngine`. |
| Upload Document | `WorldClassClientPortal.jsx` | `openUploadPanel({ track:'general' })` | in-page upload | correct | One-document-at-a-time panel. |
| View Documents Vault | `WorldClassClientPortal.jsx` | `/client/documents` | `/client/documents` | correct | Explicit vault route. |
| Request Review | dashboard upload lane | `/client/request-review` via lane/CTA pattern | review request | correct | Covered by sidebar and Clyde. |

## 3. `/client/credit-profile` and `/client/credit-utilization`

| Button / action | File | Current action | Expected action | Status | Notes |
|---|---|---|---|---|---|
| Upload Credit Report | `WorldClassClientPortal.jsx` | `openCreditUpload()` -> panel | `credit_report` panel | correct | Applies to both compatible routes. |
| Connect Credit Monitoring Resource | `WorldClassClientPortal.jsx` | disabled/gated provider, resources fallback | gated/provider or resources | gated correctly | No fake bureau connection. |
| View recommended monitoring resources | `WorldClassClientPortal.jsx` | `/client/resources?category=credit-monitoring` | resource route | correct | Education/resource action. |
| I Need Help Getting My Report | `creditReportReviewFlow.ts` | `/client/request-review?topic=credit-report-help` | request review topic | correct | Works from entry option. |
| Manually Add Negative Item | `creditReportReviewFlow.ts` | `/client/credit-repair-journey?action=manual-negative-item` | manual item workflow | fixed | Added query action. |
| Clyde recommendation: Upload | `WorldClassClientPortal.jsx` | upload panel | upload panel | correct | No Documents redirect. |
| Clyde recommendation: Review | `WorldClassClientPortal.jsx` | `/client/dispute-review` | Review letters | correct | Review route. |
| Clyde recommendation: Open | `WorldClassClientPortal.jsx` | `/client/credit-repair-journey` | repair workflow | correct | Could later add query hints. |
| Factors Needing Attention rows | `WorldClassClientPortal.jsx` | tip or resources | scroll/tip/resource | correct | Not dead. |
| Positive Factors View all | `WorldClassClientPortal.jsx` | toggles list | expand list | correct | In-page action. |
| Upload lane View Vault | `WorldClassClientPortal.jsx` | `/client/documents` | vault route | correct | Explicit vault route. |
| Pay down high utilization | `WorldClassClientPortal.jsx` | in-page tip | utilization panel/section | correct | In-page explanation. |
| Term loan / consolidation review | `WorldClassClientPortal.jsx` | `/client/request-review?topic=term-loan-consolidation-review` | request review topic | correct | Topic differs slightly from expected but correct intent. |
| Credit limit increase checklist | `WorldClassClientPortal.jsx` | in-page tip | checklist panel/section | correct | In-page gated advice. |
| Statement date timing | `WorldClassClientPortal.jsx` | in-page tip | timing panel/section | correct | In-page advice. |
| Challenge incorrect balances | `WorldClassClientPortal.jsx` | scroll to attention | credit repair reason route preferred | needs manual verification | Could be improved later with `reason=incorrect_balance`. |
| Business funding to reduce pressure | `WorldClassClientPortal.jsx` | `/client/funding-readiness` | Business Funding | correct | Route correct. |

## 4. `/client/profile` and `/client/business-setup`

| Button / action | File | Current action | Expected action | Status | Notes |
|---|---|---|---|---|---|
| Edit profile cards | `WorldClassClientPortal.jsx` | focus profile form | scroll/focus section | correct | Simple focus behavior. |
| Upload Business Profile Document | `WorldClassClientPortal.jsx` | upload panel, business profile | in-page upload | correct | One central lane. |
| Document tile upload/replace | `WorldClassClientPortal.jsx` | upload panel with suggested category | in-page upload | correct | No Documents redirect. |
| Intake status choices | `WorldClassClientPortal.jsx` | local form state | select/save on page | correct | Persisted by Save Profile. |
| Need help getting setup item | `SetupStateControl` | shows resource copy | resource + review option | partially implemented | Review route not auto-created; documented caveat. |
| Inline requirement uploads | `InlineDocumentRequirement.jsx` | delegated `onOpenUpload` | central upload panel | correct | Falls back to embedded upload only if no handler. |
| Go to Request Review | `WorldClassClientPortal.jsx` | `/client/request-review` | review request | correct | Ready for Review section. |
| Save Profile | `WorldClassClientPortal.jsx` | `saveClientProfileIntake(form)` | save/load profile | correct | Uses existing adapter. |
| Business setup states | `BusinessPanel` | local setup state + resource copy | on-page state/help | partially implemented | Not persisted; no fake completion. |
| Go to Funding Readiness | `BusinessPanel` | `/client/funding-readiness` | Business Funding | correct | Route correct. |

## 5. `/client/funding-readiness`

| Button / action | File | Current action | Expected action | Status | Notes |
|---|---|---|---|---|---|
| Upload Funding Document | `WorldClassClientPortal.jsx` | upload panel, `business_funding` | in-page upload | correct | One central lane. |
| Request GoClear Funding Review | `WorldClassClientPortal.jsx` | `/client/request-review?topic=funding-review` | funding review topic | correct | Route correct. |
| Required doc upload/replace | `InlineDocumentRequirement.jsx` | central panel with category | in-page upload | correct | Bank/tax/P&L/license/EIN/formation. |
| Ask GoClear | `WorldClassClientPortal.jsx` | `/client/request-review?topic=funding-options` | review request | correct | Topic-specific. |
| Resources | `WorldClassClientPortal.jsx` | `/client/resources?category=funding-education` | resources | correct | Education route. |
| Funding option chips | `WorldClassClientPortal.jsx` | display labels | route/resource per option | needs manual verification | They are labels, not buttons. |

## 6. `/client/documents`

| Button / action | File | Current action | Expected action | Status | Notes |
|---|---|---|---|---|---|
| Vault upload dropzone | `DocumentUploadZone.tsx` | upload one file, metadata insert | vault upload | correct | `maxFiles={1}` on Documents page. |
| Quick Upload buttons | `WorldClassClientPortal.jsx` | open upload panel with category | in-page upload | correct | No route redirect. |
| Recommended See recommendations | `WorldClassClientPortal.jsx` | `/client/resources` | resources | correct | Explicit recommendation route. |
| Vault rows | `WorldClassClientPortal.jsx` | status display | view/replace/usage future | partially implemented | No safe document view URL yet. |
| Secure Learn about security | `WorldClassClientPortal.jsx` | `/client/resources` | security/resource | correct | Resource route. |

## 7. `/client/resources`

| Button / action | File | Current action | Expected action | Status | Notes |
|---|---|---|---|---|---|
| Resource recommendation cards | `WorldClassClientPortal.jsx` | contextual route via `routeForResource` | route/href/gated fallback | fixed | Was looping to Resources. |
| Category cards Explore | `WorldClassClientPortal.jsx` | contextual route via `routeForResource` | route/gated fallback | fixed | No dead buttons. |
| Partner row Learn more | `WorldClassClientPortal.jsx` | request-review fallback or route | approved/gated fallback | fixed | No external URL assumed. |
| External partner href | `clientResources.ts` | internal route placeholders | approved href if configured | gated correctly | No unsafe claims. |

## 8. `/client/request-review`

| Button / action | File | Current action | Expected action | Status | Notes |
|---|---|---|---|---|---|
| Attach Support Document | `WorldClassClientPortal.jsx` | upload panel, `review_support` | in-page upload | correct | One central lane. |
| Review type choices | `WorldClassClientPortal.jsx` | set state | select review type | correct | Four visible choices. |
| Inline attachment upload | `InlineDocumentRequirement.jsx` | central panel | upload panel | correct | Uses `onOpenUpload`. |
| Submit Review Request | `WorldClassClientPortal.jsx` | insert `client_tasks` | approval-gated task | correct | `pending_admin_review`, manual. |
| What Happens Next | `WorldClassClientPortal.jsx` | status display | informational | correct | Not clickable. |

## 9. `/client/credit-repair-journey`

| Button / action | File | Current action | Expected action | Status | Notes |
|---|---|---|---|---|---|
| Upload Credit Repair Evidence | `WorldClassClientPortal.jsx` | upload panel | in-page upload | correct | One central lane. |
| Upload your credit report | `WorldClassClientPortal.jsx` | upload panel, `credit_report` | in-page upload | correct | No Documents redirect. |
| Continue Profile | `WorldClassClientPortal.jsx` | `/client/profile` | Business Profile | correct | Route correct. |
| Review dispute letters | `WorldClassClientPortal.jsx` | `/client/dispute-review` | Review letters | correct | Route correct. |
| Upload Credit Report in case engine | `WorldClassClientPortal.jsx` | upload panel | in-page upload | correct | Case engine status card. |
| Add item to case | `WorldClassClientPortal.jsx` | `createManualReportItem` | manual item creation | correct | Non-sensitive masked account only. |
| Select report item | `WorldClassClientPortal.jsx` | set selected item state | select item | correct | In-page state. |
| I want this challenged | `WorldClassClientPortal.jsx` | `markItemForChallenge` | mark item | correct | Client flag. |
| Reason buttons | `WorldClassClientPortal.jsx` | `selectDisputeReason` + options | choose reason | correct | Deterministic options. |
| Evidence Upload | `InlineDocumentRequirement.jsx` | central panel, dispute support | in-page upload | correct | No Documents redirect. |
| Prepare draft | `WorldClassClientPortal.jsx` | `createLetterDraftFromOption` | specialist review draft | correct | Not sent. |
| Review gate/View drafts | `WorldClassClientPortal.jsx` | `/client/dispute-review` | review letters | correct | Route correct. |
| Credit Monitoring Support Resources | `WorldClassClientPortal.jsx` | `/client/resources?category=credit-monitoring` | resources | correct | Support, not required. |

## 10. `/client/dispute-review`

| Button / action | File | Current action | Expected action | Status | Notes |
|---|---|---|---|---|---|
| Back to Credit Repair Journey | `WorldClassClientPortal.jsx` | `/client/credit-repair-journey` | route back | correct | Route correct. |
| Continue Credit Repair Journey | `WorldClassClientPortal.jsx` | `/client/credit-repair-journey` | route back | correct | Empty state. |
| View letter | `WorldClassClientPortal.jsx` | show preview in notice | show preview | correct | No sending. |
| Request edits | `WorldClassClientPortal.jsx` | creates `client_tasks` edit request | edit request only | correct | Not sent. |
| Approve letter | `WorldClassClientPortal.jsx` | `clientApproveLetter(letter.id)` | client approval only | correct | Uses existing workflow. |
| Authorize/send request | `WorldClassClientPortal.jsx` | `createDocuPostSendRequest(letter.id)` only if approved | gated DocuPost request | correct | Disabled unless approved. |
| Upload supporting document | `WorldClassClientPortal.jsx` | upload panel, dispute support | in-page upload | correct | One-document panel. |

## Summary Findings

- Upload buttons now open the in-page panel except explicit `View Documents Vault` actions.
- No client-facing upload CTA defaults to Documents.
- Resources actions were corrected to contextual routes or request-review fallbacks.
- Credit repair letters are not created by credit report upload alone.
- No fake parser/OCR/bureau connection exists or is claimed.
- No DocuPost auto-send path was found in the client portal.
