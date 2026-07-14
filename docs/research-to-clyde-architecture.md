# Research-to-Clyde Architecture and Safety Boundaries

## Responsibility boundary

Alpha may discover public techniques and summarize public sources. It has no Supabase, client report, PII, private evidence, client-action, approval, or mailing access. Its output is a sanitized discovery artifact, never client guidance.

The Nexus Research Department reuses the canonical research inbox and source registry. It hashes sources, separates claims, records authority/contradiction/evidence/risk, preserves rejected claims, and creates versioned strategy candidates. Only an active admin can approve, reject, request changes, or retire a version. Approval notes and events are durable.

Clyde reads structured client-visible discrepancies and an approved exact strategy version. Clyde distinguishes Nexus-detected facts, client facts, approved education, uncertainty, limitations, and next actions. Clyde asks only facts the report cannot determine and never reads raw research or rejected claims.

GoClear handles defined exceptions: low-confidence inputs, no safe approved strategy for a high-impact issue, conflicting strategies, contradictory evidence, identity-theft indicators, complaints/legal threats, generation/integrity failures, blocked drafts, or an explicit client request. Negative accounts, ordinary collections, objective balance differences, evidence requests, and safe drafts are not exceptions by themselves.

## Approval lifecycle and versioning

`source → claims → evidence/risk review → strategy definition → immutable strategy version → admin approval → deterministic match → Clyde card`.

Edits create a new version. Retired versions cannot create new selections, while historical selections preserve their version. Rejected claims remain in research history and cannot appear in client-safe strategy text.

## Evidence security

Evidence uploads reuse `client-documents`, its existing file/type/size checks, tenant membership, protected storage, and signed-access architecture. A separate evidence link attaches the document to a selection and discrepancy. Alpha never receives evidence. Raw evidence is not placed in prompts. Admin rejection requires a reason.

## Draft safety

Outputs use structured report facts, client-confirmed facts, an exact strategy/template version, masked references, provenance, and required disclaimers. The validator blocks guarantees, universal deletion claims, automatic damages, “must delete,” and universal original-contract claims. Every output remains a draft requiring client review. Mail creation is structurally false; DocuPost is not invoked.
