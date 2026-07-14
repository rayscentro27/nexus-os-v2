#!/usr/bin/env python3
from pathlib import Path
r=Path(__file__).resolve().parents[2];w=(r/"scripts/credit/process_credit_analysis_queue.py").read_text();p=(r/"scripts/credit/parse_uploaded_credit_report.py").read_text()
for value in ("--once","--dry-run","--job-id","--requeue-stale","--verify-result","lease_expires_at","claimed_by","max_attempts","worker_version","ruleset_version","failed_retryable","failed_permanent","status=eq.queued","--analysis-job-id"):assert value in w+p
assert "while True" not in w and "json.dumps(parse_result['accounts'])" not in p and "docupost" not in w.lower()
assert "safe_failure" in w and "canonical persistence verification failed" in w
print("PASS: bounded leased worker, retries, preserved attempts, native JSONB, sanitized failure, no mail")
