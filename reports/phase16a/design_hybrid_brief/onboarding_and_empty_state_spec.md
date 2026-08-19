# Onboarding and Empty-State Specification

## First-login flow

`authenticated → canonical client context → intake completion check → onboarding if incomplete → dashboard if complete`

The completion check must read the authoritative client profile/intake state. A page load, localStorage flag, demo mode, or presence of an auth session is not completion. If the state cannot be safely resolved, fail closed to a clear setup/error state rather than showing populated demo content.

## Recommended step sequence

1. **Welcome and goal** — explain the service and ask what the client wants to prepare for.
2. **Basic profile** — legal/preferred name, contact, and the minimum identifying context.
3. **Business situation** — business name, entity type, industry, and only relevant readiness facts.
4. **Document preparation/upload** — explain the credit report requirement and provide a secure upload action.
5. **Review and next step** — summarize what was saved, what is still missing, and when Credit Review can begin.

Save each step through the canonical client record, show progress, allow resume, and avoid collecting credit-monitoring passwords or unnecessary financial secrets.

## Required clean-client state

For a brand-new real client with no uploaded documents, report, analysis, readiness result, CRJ case, or payment record, show:

- Welcome to GoClear;
- Current stage: Account setup / Onboarding required;
- one primary action: Complete profile or Continue setup;
- journey stages with later stages marked upcoming/locked;
- Documents: “No documents yet” and why the report matters;
- Credit Review: “Not started” or “Waiting for your report”;
- Help/Hermes entry with client-safe context;
- clear support path.

## Must not appear

Do not show fake or inherited scores, document counts, synthetic recommendations, demo tasks, another client’s opportunities, certification fixtures, mock CRJ status, fake payment success, or populated activity history. Do not use a generic “0” score that could be mistaken for a measured result.

## Communicating missing information

Say what is missing, why it matters, and what the client can do next. Example: “No credit report has been uploaded yet. Uploading it lets GoClear begin the Credit Review; no score has been calculated.” Keep the message factual and non-guaranteeing.

## Progressive reveal

- Before profile completion: show profile action and basic document preparation only.
- After profile completion: reveal upload and Credit Review preparation.
- After a verified report: reveal review status and relevant education.
- After verified analysis: reveal recommendations and readiness evidence.
- After approval and real lifecycle records: reveal payment, business/funding, or future CRJ transition details.

