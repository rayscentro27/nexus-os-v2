#!/usr/bin/env python3
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[2]; worker=(root/'scripts/credit/process_credit_analysis_queue.py').read_text(); migration=(root/'supabase/migrations/20260714120000_funding_readiness_system_reviews.sql').read_text(); frontend=(root/'src/lib/creditRepairWorkflow.ts').read_text()
terms=['queued','processing','complete','failed_retryable','failed_permanent','--max-jobs','min(a.max_jobs,10)','status=eq.queued','credit_analysis_jobs_one_active_per_document','queueCreditReportAnalysis']
for t in terms: print(('PASS' if t in worker+migration+frontend else 'FAIL')+': '+t)
safe='SUPABASE_SERVICE_ROLE_KEY' not in frontend and 'docupost' not in worker.lower() and 'while True' not in worker
print(('PASS' if safe else 'FAIL')+': bounded and no browser secret or mailing')
sys.exit(0 if all(t in worker+migration+frontend for t in terms) and safe else 1)
