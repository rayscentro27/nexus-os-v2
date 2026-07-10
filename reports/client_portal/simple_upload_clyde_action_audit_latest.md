# Simple Upload + Clyde Action Audit

- Current world-class design preserved: `True`
- Old design restored: `False`
- Starting commit: `1c592f9`

## Findings

- Home, Credit Profile, Business Profile, Business Funding, Request Review, Dispute Review, and Credit Repair had upload CTAs that either routed to Documents or opened separate inline upload zones.
- Requirement cards could create upload clutter because each card owned its own embedded upload zone.
- Clyde drawer existed, but it was mostly static and did not trigger the upload flow directly.
- Documents page was acting as both vault and default upload destination.

## Patch Plan Applied

- Add one reusable in-page upload panel.
- Keep Documents as the master vault.
- Route upload CTAs to `openUploadPanel(...)`.
- Keep one-document-at-a-time behavior.
- Add deterministic document classification from context and filename only.
- Add a Clyde action engine for page-aware quick actions and answers.
