# Open Source Credit Repair Engine Research — Latest

**Audit Date:** 2026-07-13
**Auditor:** Nexus Engine Audit Sprint
**Status:** Complete

---

## Repos Inspected

### 1. Wadprog/RepairCredit-
- **URL:** https://github.com/Wadprog/RepairCredit-
- **Language/Framework:** Node.js (Express) + React client
- **Stars:** 10 | **Forks:** 6 | **Last Active:** ~2022
- **What it does:** Automated credit repair app that contacts credit bureaus
- **Parses credit reports:** No evidence of real PDF/HTML report parsing
- **Generates dispute letters:** Partially — template-based
- **Tracks dispute timelines:** Basic status tracking
- **Handles PDFs/HTML/TXT:** No real PDF extraction found
- **Safe to integrate:** No — incomplete, no real parser, unclear security posture
- **License risk:** No explicit license found (defaults to restrictive)
- **Stores sensitive data unsafely:** Risk — no evidence of SSN/DOB guardrails
- **Duplicates Nexus:** Partially — has CRM-like workflow, but no real parser
- **Recommendation:** REJECT — too incomplete, no real parsing engine

### 2. Bot2botheavy/Fcra-dispute-engine
- **URL:** https://github.com/Bot2botheavy/Fcra-dispute-engine
- **Language/Framework:** Node.js + Python (planned)
- **Stars:** ~0 | **Commits:** 2 | **Status:** Phase 1 — System Design only
- **What it does:** Planned FCRA dispute system — architecture doc only
- **Parses credit reports:** No code yet
- **Generates dispute letters:** Planned, not implemented
- **Tracks dispute timelines:** No
- **Handles PDFs/HTML/TXT:** No
- **Safe to integrate:** N/A — no code
- **License risk:** MIT license present
- **Stores sensitive data unsafely:** N/A
- **Duplicates Nexus:** No — aspirational only
- **Recommendation:** REJECT — no implementable code

### 3. Rorschach3/credit-clarity-ai-assist
- **URL:** https://github.com/Rorschach3/credit-clarity-ai-assist
- **Language/Framework:** React + Flask (Python), Tesseract OCR, PyTorch
- **Stars:** ~148 commits | **Status:** Active
- **What it does:** AI-powered credit report analysis + dispute letter generation with OCR
- **Parses credit reports:** Yes — OCR + NLP extraction
- **Generates dispute letters:** Yes — AI-generated FCRA-compliant letters
- **Tracks dispute timelines:** Yes — dashboard with progress tracking
- **Handles PDFs/HTML/TXT:** Yes — Tesseract OCR for images, text extraction
- **Safe to integrate:** Moderate — heavy AI dependencies, may not match Nexus stack
- **License risk:** Unclear — no explicit license found
- **Stores sensitive data unsafely:** Concern — uses Supabase but unclear guardrails
- **Duplicates Nexus:** Partially — similar workflow but different tech stack
- **Recommendation:** REFERENCE ONLY — useful OCR+NLP approach, but too heavy for direct integration

### 4. itsbergomy/Dispute-GPT
- **URL:** https://github.com/itsbergomy/Dispute-GPT
- **Language/Framework:** Python (Flask), OpenAI API
- **Stars:** 3 | **Commits:** 9
- **What it does:** Python script for credit report discrepancy handling + dispute letter generation via OpenAI
- **Parses credit reports:** Yes — PDF text extraction via PyPDF
- **Generates dispute letters:** Yes — AI-generated via GPT
- **Tracks dispute timelines:** No
- **Handles PDFs/HTML/TXT:** PDF only via PyPDF
- **Safe to integrate:** Low — requires OpenAI API key, no guardrails
- **License risk:** MIT
- **Stores sensitive data unsafely:** High — sends data to OpenAI
- **Duplicates Nexus:** Partially — similar goal, different approach
- **Recommendation:** REFERENCE ONLY — PyPDF extraction approach is useful, but AI dependency is risky

### 5. moov-io/metro2
- **URL:** https://github.com/moov-io/metro2
- **Language/Framework:** Go
- **Stars:** 127 | **Forks:** 57 | **License:** Apache-2.0
- **What it does:** Metro 2 consumer credit history report reader/writer/validator
- **Parses credit reports:** Yes — but only Metro 2 format files (not consumer PDFs)
- **Generates dispute letters:** No
- **Tracks dispute timelines:** No
- **Handles PDFs/HTML/TXT:** No — Metro 2 format only (.dat/.json)
- **Safe to integrate:** Yes — well-maintained, production-grade
- **License risk:** Apache-2.0 — safe
- **Stores sensitive data unsafely:** No — does not persist data
- **Duplicates Nexus:** No — different format entirely
- **Recommendation:** POSTPONED — useful for furnisher-side reporting, not consumer report parsing

### 6. ibernabel/creditgraph-parser
- **URL:** https://github.com/ibernabel/creditgraph-parser
- **Language/Framework:** Python (FastAPI)
- **What it does:** Converts credit report PDFs into structured JSON using AI patterns with PII scrubbing
- **Parses credit reports:** Yes — PDF to structured JSON
- **Generates dispute letters:** No
- **Tracks dispute timelines:** No
- **Handles PDFs/HTML/TXT:** PDF
- **Safe to integrate:** Moderate — uses AI but has PII scrubbing
- **License risk:** Unclear
- **Duplicates Nexus:** Partially — parser approach is similar
- **Recommendation:** REFERENCE ONLY — PII scrubbing pattern is useful

### 7. meldofficial9/credit-repair-ai
- **URL:** https://github.com/meldofficial9/credit-repair-ai
- **Language/Framework:** Unknown
- **What it does:** Automated credit dispute letter generator with certified mail via Lob
- **Parses credit reports:** Unknown
- **Generates dispute letters:** Yes
- **Tracks dispute timelines:** Unknown
- **Safe to integrate:** Unknown — Lob integration
- **Recommendation:** REFERENCE ONLY — Lob mailing approach is interesting for DocuPost

### 8. DisputeAI (commercial)
- **URL:** https://www.disputeai.io/
- **Type:** Commercial SaaS (not open source)
- **What it does:** AI-generated FCRA-compliant dispute letters, report upload + extraction
- **Relevance:** Shows market validation for Nexus approach
- **Recommendation:** REFERENCE ONLY — validates Nexus product direction

---

## Summary

| Repo | Useful For | Integration Risk | Recommendation |
|------|-----------|-----------------|----------------|
| Wadprog/RepairCredit- | Nothing — too incomplete | High | REJECT |
| Bot2botheavy/Fcra-dispute-engine | Nothing — no code | N/A | REJECT |
| credit-clarity-ai-assist | OCR+NLP approach reference | Medium | REFERENCE ONLY |
| Dispute-GPT | PyPDF extraction pattern | Medium | REFERENCE ONLY |
| moov-io/metro2 | Metro 2 format (future) | Low | POSTPONED |
| creditgraph-parser | PII scrubbing pattern | Medium | REFERENCE ONLY |
| credit-repair-ai | Lob mailing pattern | Low | REFERENCE ONLY |
| DisputeAI | Market validation | N/A | REFERENCE |

## Key Findings

1. **No open-source tool provides a complete, production-ready credit report parser + dispute engine** that Nexus can adopt wholesale.
2. **moov-io/metro2** is the most mature but targets Metro 2 format files, not consumer PDF/HTML reports.
3. **OCR approaches** (Tesseract + OpenCV) are well-established but require local dependency installation.
4. **AI-powered parsers** (Dispute-GPT, creditgraph-parser) exist but add external API dependencies Nexus should avoid for core parsing.
5. **Nexus's existing parser approach** (regex-based text extraction + pattern matching) is actually the right architecture for a self-contained engine. The gap is in PDF text extraction, not parsing logic.
6. **The real bottleneck** is getting text out of PDFs — pypdf works for text-based PDFs, Tesseract for scanned images.

## Recommendation

Nexus should:
1. Use pypdf for text-based PDF extraction (already works locally)
2. Add optional Tesseract OCR for scanned/image PDFs
3. Keep the existing regex parser but improve pattern coverage
4. Not adopt any external credit repair repo directly
5. Focus on proving the local engine flow end-to-end
