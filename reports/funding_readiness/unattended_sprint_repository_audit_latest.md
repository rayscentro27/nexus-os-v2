# Unattended Funding Readiness Sprint — Repository Audit

- Date: 2026-07-14
- Starting commit: `c5bb256eb0647b8df454308d30ffea986d8eca65`
- Branch: `main`
- Existing dirty work: runtime, cache, research, Alpha, Telegram, and work-order artifacts were present before this sprint and remain out of scope.

## Active architecture

- Uploads: `client_documents` and the `client-documents` storage bucket.
- Parser worker: `scripts/credit/parse_uploaded_credit_report.py` using verified PDF text extraction and server-only Supabase credentials.
- Parser storage: `credit_report_parser_results`, created by `20260713120000_credit_report_parser_results.sql`.
- Frontend normalization: `src/lib/creditRepairWorkflow.ts`; admin display: `CreditSpecialistWorkbench.jsx`.
- Credit/report cases and letters: existing credit repair compatibility tables and `creditRepairCaseEngine.ts`; DocuPost remains approval-gated.
- Client data: canonical `client_profiles`, `business_profile_requirements`, `readiness_scores`, documents, tasks, and approved guidance.
- Backend options found: Netlify JavaScript functions cannot safely host the existing Python/PDF dependency path without a separate deployment. The implemented minimal path is an admin-only database queue plus bounded local worker.

## Parser shape

The table stores arrays in JSONB columns: `accounts`, `inquiries`, `personal_info_variations`, `negative_candidates`, `structured_item_drafts`, and `dispute_strategy_suggestions`; objects use `utilization_summary`; the loader now returns normalized arrays and derived counts.
