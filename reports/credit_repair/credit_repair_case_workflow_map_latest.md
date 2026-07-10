# Credit Repair Case Workflow Map

| Step | Status | File / function / table | Button involved |
|---|---|---|---|
| Client uploads credit report | Implemented | `DocumentUploadZone.tsx`, `client_documents` | Upload Credit Report |
| Document row created | Implemented | `writeDocumentMetadata(...)`, `client_documents` | Upload panel |
| Status Pending GoClear Review | Implemented | `status`, `goclear_review_status` | Upload panel result |
| Credit Repair Case exists/created | Partially implemented | `getOrCreateCreditRepairCase(...)`, `credit_repair_cases` | Credit Repair Case page load |
| Report items created | Partially implemented | `createManualReportItem(...)`, `credit_report_items` | Add item to case |
| Automatic report parsing | Missing | none | none |
| Client selects items to challenge | Implemented | `markItemForChallenge(...)` | I want this challenged |
| Client selects reason | Implemented | `selectDisputeReason(...)`, `credit_dispute_strategies` | reason buttons |
| Nexus generates letter options | Implemented | `generateDisputeLetterOptions(...)`, `disputeStrategyKnowledge.ts` | reason buttons |
| Draft created | Implemented | `createLetterDraftFromOption(...)`, `credit_dispute_letter_options`, legacy letters | Prepare draft |
| GoClear specialist review | Implemented | `CreditSpecialistWorkbench.jsx`, `specialistApproveLetter(...)` | Approve for Client |
| Specialist edits / requests info | Partially implemented | admin workbench + client_tasks edit requests | Request edits |
| Client reviews approved draft | Implemented | `/client/dispute-review`, `loadCreditRepairJourney(...)` | View letter |
| Client approves / requests edits | Implemented | `clientApproveLetter(...)`, `client_tasks` | Approve letter / Request edits |
| DocuPost/send request | Implemented and gated | `createDocuPostSendRequest(...)`, `docupost_mail_jobs` | Authorize/send request |
| Tracking status updated | Partially implemented | legacy letter/mail job status | Mail job status |
| Outcome recorded | Partially implemented | `recordDisputeOutcome(...)`, `credit_dispute_outcomes` | admin/specialist workflow |
| Clyde recommends next action | Implemented | `clydeActionEngine.ts` | Clyde panel/drawer |

## Desired Flow Status

Client uploads credit report -> document is pending GoClear Review -> case page creates/loads active case -> report items are manual/specialist-created until parser exists -> client selects items/reasons -> deterministic options are generated -> draft goes to specialist review -> specialist approves for client -> client approves or requests edits -> DocuPost request is created only after approval -> outcome tracking is recorded manually/admin-side today.
