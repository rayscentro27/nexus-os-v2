# Postponed External Integrations — Latest

**Date:** 2026-07-13
**Status:** Explicit Rejection/Postponement List

---

## Postponed (Not Now)

### Plaid
- **What:** Bank account linking for income/assets verification
- **Why postponed:** Not relevant to credit report parsing engine. Adds API key dependency, compliance burden, and client-facing UX that is not needed for engine proof.
- **When to revisit:** After engine is proven with fake data and before real client onboarding.
- **Prerequisites:** Plaid account, legal review, client consent flow.

### moov-io/metro2
- **What:** Metro 2 format reader/writer/validator
- **Why postponed:** Metro 2 is the format furnishers use to report to bureaus. Nexus is building a consumer-facing dispute tool, not a furnisher reporting tool. Useful for understanding bureau data formats, but not directly usable for parsing consumer PDFs.
- **When to revisit:** If Nexus ever needs to generate Metro 2 files for furnisher disputes.
- **Prerequisites:** Actual Metro 2 file format requirements.

### n8n/Activepieces
- **What:** Workflow automation platforms
- **Why postponed:** Nexus already has the workflow logic in code. Adding n8n/Activepieces would add infrastructure complexity without solving the core parsing/engine problem. Automation can be added after the engine works.
- **When to revisit:** After engine proof and before scaling to multiple clients.
- **Prerequisites:** Engine must work first.

### DocuPost API Integration
- **What:** Automated certified mail sending via DocuPost
- **Why postponed:** Workflow structure exists but no API client is built. Manual marking only. This is the final step in the pipeline and should be integrated last, after parsing, item creation, dispute strategy, letter generation, specialist review, and client approval all work.
- **When to revisit:** After all approval gates are proven working.
- **Prerequisites:** DocuPost API account, webhook handling, address verification.

---

## Rejected (Never Do)

### Bureau Login/Scraping
- **What:** Logging into Experian/Equifax/TransUnion portals to pull reports
- **Why rejected:** Violates bureau terms of service. Security risk. Client credential collection. Legal liability. Technical fragility.
- **Alternative:** Client uploads report manually or via monitoring service download.

### Automatic Client-Facing Letters from Parser
- **What:** Generating final dispute letters directly from parser output without specialist review
- **Why rejected:** Parser output is suggested extraction only. Letters require legal review. Auto-generation could produce inaccurate or non-compliant letters. Client safety risk.

### Direct DocuPost Send Without Approvals
- **What:** Sending letters via DocuPost without specialist review AND client approval
- **Why rejected:** No letter should be sent without both specialist and client approval. This is a core safety gate that must never be bypassed.

---

## Key Principle

Nexus adds integrations only after the core engine is proven locally. Every integration adds dependency, compliance, and maintenance burden. The engine must work with zero external dependencies before any are added.
