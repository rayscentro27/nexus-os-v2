# Nexus Client Intake Automation Policy

See [NEXUS_AUTOMATION_LEVELS.md](NEXUS_AUTOMATION_LEVELS.md). Covers GoClear / Apex Client Intake,
Credit Repair / Funding Guidance, and Client Portal.

- **Level 1 (autonomous):** lead scoring, readiness checklists, internal cards/reports, internal
  guidance research.
- **Level 2 (approval-gated):** client notification, client contact, client-facing scheduling,
  client-facing guidance delivery, client portal publishing.
- **Level 3 (blocked):** client data exposure externally, external AI on customer/credit-sensitive
  data, publishing compliance-sensitive claims without review.

Credit/funding guidance carries high compliance risk: research is internal, all client-facing
delivery is gated, and a compliance review is required before any client-facing claim. Client data
stays internal — never exposed externally.

## Client Workflow Engine

The full signup → funding-ready engine (stages, credit/business/funding scoring, letters, mailing,
reminders, Hermes recommendations) is documented in
[NEXUS_CLIENT_WORKFLOW_ENGINE.md](NEXUS_CLIENT_WORKFLOW_ENGINE.md). It enforces this policy: internal
work is autonomous (Level 1); sending/contact/publishing/mailing/dispute-submission/funding-
applications are approval-gated (Level 2); SmartCredit password storage/scraping, auto-mailing,
auto-filing, auto-opening accounts, auto-applying for funding, and external AI on client credit data
are blocked (Level 3).
