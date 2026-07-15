# Controlled Three-Person Tester Pilot Task Checklist

**Fixture:** `controlled-pilot-v1`
**Build baseline:** `68070d352bb0337fab07a5e54260f99979161c0f` plus the verified Phase 5 continuation working tree
**Scope:** synthetic Personas A, B, and C only
**Execution mode:** manual-like Playwright through the real client/admin UI; no authentication bypass or client impersonation

Session references are intentionally sanitized. Protected database IDs, credentials, tokens, document contents, storage paths, and account references are not included in this report.

## Required checklist

| Task | Persona A | Persona B | Persona C | Evidence state |
|---|---:|---:|---:|---|
| 1. Login and synthetic-persona isolation | Attempted | Attempted | Attempted | Passed in controlled pilot UI coverage |
| 2. Understand Funding Readiness, stage, blocker, and next action | Attempted | Attempted | Attempted | Passed for dashboard comprehension coverage |
| 3. Credit / exception workflow | Normal discrepancy and approved strategy | Genuine exception and specialist-review path | Purchased-debt documentation review | Passed |
| 4. Business Foundation and Bankability workflow | Attempted | Attempted | Attempted | Passed for requirement and gap visibility |
| 5. Inline synthetic upload | Credit evidence | Contextual requirement available | Purchased-debt evidence | Passed; protected upload flow stayed on page |
| 6. Documents Vault | Attempted | Available | Attempted | Passed; category and linkage visible |
| 7. Clyde contextual guidance | Attempted | Attempted with uncertainty | Available in portal | Passed |
| 8. Funding Readiness comprehension | Attempted | Exception/blocker state | Documentation requirement state | Passed |
| 9. Resources and contextual offer | Available | Available | Available | Passed in portal route coverage |
| 10. Request Review | Eligibility and no-guarantee language | Blocked until specialist review | Eligibility and missing requirements | Passed; no submission executed |
| 11. Structured feedback | Medium observation | Low observation | Medium observation | Persisted; backlog-only |
| 12. Session closeout | Completed | Completed | Completed | Persisted through Tester Readiness UI |

## Persona-specific acceptance checks

- Persona A: approved strategy, client decision, evidence requirement, safe draft, follow-up comparison, and progressing journey state remained visible.
- Persona B: genuine exception remained the primary blocker; specialist review and uncertainty language remained visible; no unsafe strategy or false completion state appeared.
- Persona C: purchased-debt documentation requirement, contextual evidence upload, approved documentation strategy, safe draft, comparison, and persisted journey progress remained visible.

## Responsive checklist

The controlled suite exercised 1920×1080, 1366×768, 768×1024, and 390×844. It checked horizontal overflow, navigation, Continue/next action, Clyde access or guidance, and primary controls.

**Result:** 9/9 controlled pilot browser tests passed; no required test was skipped.
