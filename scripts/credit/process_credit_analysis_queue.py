#!/usr/bin/env python3
"""Bounded worker for allowlisted credit-report analysis jobs; never a daemon."""
from __future__ import annotations
import argparse, json, os, ssl, subprocess, sys, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path
import certifi

SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
ALLOWED_STATUSES = {"queued", "processing", "complete", "failed", "needs_manual_review"}
def load_env() -> dict[str, str]:
    result: dict[str, str] = {}
    for name in (".env.local", ".env"):
        path = Path(name)
        if path.exists():
            for line in path.read_text(errors="ignore").splitlines():
                if "=" in line and not line.lstrip().startswith("#"):
                    key, value = line.split("=", 1); result[key.strip()] = value.strip().strip('"').strip("'")
    result.update({k: v for k, v in os.environ.items() if v}); return result
def request(method: str, url: str, key: str, path: str, body=None):
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json", "Prefer": "return=representation"}
    req = urllib.request.Request(f"{url}/rest/v1/{path}", data=json.dumps(body).encode() if body is not None else None, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30, context=SSL_CONTEXT) as response: return json.loads(response.read().decode() or "[]")
def safe_failure(error: Exception) -> str:
    return str(error).replace(os.getenv("SUPABASE_SERVICE_ROLE_KEY", "__never__"), "[redacted]")[:500]
def now() -> str: return datetime.now(timezone.utc).isoformat()
def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--once", action="store_true"); parser.add_argument("--max-jobs", type=int, default=1); args = parser.parse_args()
    limit = 1 if args.once else max(1, min(args.max_jobs, 10))
    env = load_env(); url = env.get("SUPABASE_URL"); key = env.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key: print("ERROR: server-side Supabase environment is required.", file=sys.stderr); return 1
    jobs = request("GET", url, key, f"credit_analysis_jobs?status=eq.queued&select=id,document_id&order=created_at.asc&limit={limit}")
    if not jobs: print("No queued credit-report analysis jobs."); return 0
    failures = 0
    for job in jobs:
        job_id, document_id = job["id"], job["document_id"]
        claimed = request("PATCH", url, key, f"credit_analysis_jobs?id=eq.{job_id}&status=eq.queued", {"status":"processing","claimed_at":now(),"attempt_count":1})
        if not claimed: print(f"Skipped already-claimed job {job_id}"); continue
        print(f"Processing allowlisted credit analysis job {job_id} for document {document_id}")
        try:
            completed = subprocess.run([sys.executable, "scripts/credit/parse_uploaded_credit_report.py", "--document-id", document_id, "--out", "reports/credit_repair/live_upload_parser_results"], cwd=Path(__file__).resolve().parents[2], check=False)
            if completed.returncode != 0: raise RuntimeError(f"parser exited with code {completed.returncode}")
            parser_rows = request("GET", url, key, f"credit_report_parser_results?document_id=eq.{document_id}&extraction_success=eq.true&select=id&order=created_at.desc&limit=1")
            review_rows = request("GET", url, key, f"credit_report_system_reviews?document_id=eq.{document_id}&select=id&order=created_at.desc&limit=1")
            if not parser_rows or not review_rows: raise RuntimeError("verified parser result or system review missing after processing")
            request("PATCH", url, key, f"credit_analysis_jobs?id=eq.{job_id}&status=eq.processing", {"status":"complete","parser_result_id":parser_rows[0]["id"],"system_review_id":review_rows[0]["id"],"completed_at":now(),"failure_code":None,"failure_message":None})
            print(f"Analysis complete for job {job_id}")
        except Exception as error:
            failures += 1; request("PATCH", url, key, f"credit_analysis_jobs?id=eq.{job_id}", {"status":"failed","failure_code":"ANALYSIS_FAILED","failure_message":safe_failure(error),"completed_at":now()}); print(f"Analysis failed for job {job_id}: {safe_failure(error)}", file=sys.stderr)
    return 1 if failures else 0
if __name__ == "__main__": raise SystemExit(main())
