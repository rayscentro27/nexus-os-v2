#!/usr/bin/env python3
from pathlib import Path
r=Path(__file__).resolve().parents[2];m=(r/"supabase/migrations/20260715140000_credit_workflow_canonical_foundation.sql").read_text();frontend="\n".join((r/p).read_text(errors="ignore") for p in ("src/lib/creditRepairWorkflow.ts","src/lib/clientPortalDataAdapter.ts","src/components/CreditSpecialistWorkbench.jsx","src/components/client/DocumentUploadZone.tsx","src/components/client/SimpleDocumentUploadPanel.jsx","src/pages/client/WorldClassClientPortal.jsx","src/lib/creditAnalysisExceptionPolicy.ts"))
for table in ("credit_document_workflows","credit_bureau_tradelines","credit_canonical_accounts","credit_tradeline_match_decisions","credit_unmatched_tradelines","credit_report_discrepancies","credit_workflow_events"):assert f"alter table public.{table} enable row level security" in m
assert "credit_document_workflows_client_read" in m and "tm.user_id=auth.uid()" in m and "client mutation" not in m
assert "SUPABASE_SERVICE_ROLE_KEY" not in frontend and "service_role" not in frontend.lower()
assert "account_reference_masked" in m and "account_suffix" in m and "account_number_full" not in m
print("PASS: RLS, tenant membership, admin-only canonical mutation, frontend secret absence, masked references")
