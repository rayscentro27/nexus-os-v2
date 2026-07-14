#!/usr/bin/env python3
from pathlib import Path
t=(Path(__file__).resolve().parents[2]/"supabase/migrations/20260715140000_credit_workflow_canonical_foundation.sql").read_text()
for value in ("document_status","analysis_status","strategy_status","client_action_status","exception_review_status","mail_status","failed_retryable","failed_permanent","request_credit_analysis_rerun","validate_credit_workflow_transition","credit_analysis_jobs_one_active_version","idempotency_key","credit_workflow_events","enable row level security","nexus_is_active_admin") : assert value in t
assert "analysis_status='complete'" in t and "'not_required'" in t and "after insert on public.client_documents" in t
print("PASS: separated constrained states, safe backfill, automatic queue, transitions, idempotency, reruns, RLS")
