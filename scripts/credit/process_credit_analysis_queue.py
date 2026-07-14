#!/usr/bin/env python3
"""Bounded, leased worker for allowlisted credit-report analysis jobs; never a daemon."""
from __future__ import annotations
import argparse,json,os,platform,ssl,subprocess,sys,urllib.parse,urllib.request
from datetime import datetime,timedelta,timezone
from pathlib import Path
import certifi
SSL_CONTEXT=ssl.create_default_context(cafile=certifi.where());WORKER_VERSION="credit-worker-1.0.0";LEASE_MINUTES=15
def load_env():
    result={}
    for name in (".env.local",".env"):
        p=Path(name)
        if p.exists():
            for line in p.read_text(errors="ignore").splitlines():
                if "=" in line and not line.lstrip().startswith("#"):k,v=line.split("=",1);result[k.strip()]=v.strip().strip('"').strip("'")
    result.update({k:v for k,v in os.environ.items() if v});return result
def request(method,url,key,path,body=None):
    headers={"apikey":key,"Authorization":f"Bearer {key}","Content-Type":"application/json","Prefer":"return=representation"};req=urllib.request.Request(f"{url.rstrip('/')}/rest/v1/{path}",data=json.dumps(body).encode() if body is not None else None,headers=headers,method=method)
    with urllib.request.urlopen(req,timeout=30,context=SSL_CONTEXT) as response:return json.loads(response.read().decode() or "[]")
def now():return datetime.now(timezone.utc).isoformat()
def safe_failure(error,key):return str(error).replace(key,"[redacted]").replace(os.getenv("SUPABASE_SERVICE_ROLE_KEY","__never__"),"[redacted]")[:300]
def event(url,key,job,event_type,metadata):
    request("POST",url,key,"credit_workflow_events",{"tenant_id":job["tenant_id"],"client_id":job["client_id"],"document_id":job["document_id"],"analysis_job_id":job["id"],"event_type":event_type,"metadata":metadata,"actor_type":"worker","actor_id":WORKER_VERSION,"parser_version":job["parser_version"],"worker_version":WORKER_VERSION,"ruleset_version":job["ruleset_version"]})
def requeue_stale(url,key,dry_run=False):
    cutoff=(datetime.now(timezone.utc)-timedelta(minutes=LEASE_MINUTES)).isoformat();rows=request("GET",url,key,f"credit_analysis_jobs?status=eq.processing&lease_expires_at=lt.{urllib.parse.quote(cutoff)}&select=*");count=0
    for row in rows:
        target="queued" if row["attempt_count"]<row["max_attempts"] else "failed_permanent"
        if not dry_run:request("PATCH",url,key,f"credit_analysis_jobs?id=eq.{row['id']}&status=eq.processing",{"status":target,"claimed_by":None,"claimed_at":None,"lease_expires_at":None,"retryable":target=="queued","failure_code":"STALE_LEASE","failure_message":"Worker lease expired; no report contents were logged."});request("PATCH",url,key,f"credit_document_workflows?document_id=eq.{row['document_id']}",{"analysis_status":"queued" if target=="queued" else "failed_permanent"})
        count+=1
    print(f"Stale leases eligible for recovery: {count}");return count
def verify_job_result(url,key,job_id):
    jobs=request("GET",url,key,f"credit_analysis_jobs?id=eq.{urllib.parse.quote(job_id)}&select=id,status,document_id,parser_result_id&limit=1")
    if not jobs:
        print("ERROR: analysis job was not found.",file=sys.stderr);return 1
    job=jobs[0]
    if job["status"]!="complete" or not job.get("parser_result_id"):
        print(f"ERROR: analysis job is {job['status']}; a completed result is required.",file=sys.stderr);return 1
    result=request("GET",url,key,f"credit_report_parser_results?id=eq.{job['parser_result_id']}&select=id,accounts,inquiries,negative_candidates,extraction_success&limit=1")
    canonical=request("GET",url,key,f"credit_canonical_accounts?parser_result_id=eq.{job['parser_result_id']}&select=id")
    tradelines=request("GET",url,key,f"credit_bureau_tradelines?parser_result_id=eq.{job['parser_result_id']}&select=id")
    if not result or not result[0].get("extraction_success") or not isinstance(result[0].get("accounts"),list) or not isinstance(result[0].get("inquiries"),list) or not canonical or not tradelines:
        print("ERROR: saved analysis result failed structural verification.",file=sys.stderr);return 1
    print(json.dumps({"ok":True,"status":"complete","accounts":len(result[0]["accounts"]),"inquiries":len(result[0]["inquiries"]),"review_candidates":len(result[0].get("negative_candidates") or []),"bureau_tradelines":len(tradelines),"canonical_accounts":len(canonical)}))
    return 0
def main():
    p=argparse.ArgumentParser();p.add_argument("--once",action="store_true");p.add_argument("--max-jobs",type=int,default=1);p.add_argument("--dry-run",action="store_true");p.add_argument("--job-id");p.add_argument("--requeue-stale",action="store_true");p.add_argument("--verify-result",action="store_true");a=p.parse_args();limit=1 if a.once else max(1,min(a.max_jobs,10));env=load_env();url=env.get("SUPABASE_URL");key=env.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:print("ERROR: server-side Supabase environment is required.",file=sys.stderr);return 1
    if a.verify_result:
        if not a.job_id:print("ERROR: --verify-result requires --job-id.",file=sys.stderr);return 1
        return verify_job_result(url,key,a.job_id)
    if a.requeue_stale:requeue_stale(url,key,a.dry_run)
    selector=f"id=eq.{urllib.parse.quote(a.job_id)}&" if a.job_id else "status=eq.queued&";jobs=request("GET",url,key,f"credit_analysis_jobs?{selector}select=*&order=created_at.asc&limit={limit}")
    if not jobs:print("No queued credit-report analysis jobs.");return 0
    failures=0;worker_id=f"{platform.node()[:40]}:{os.getpid()}:{WORKER_VERSION}"
    for job in jobs:
        if job["status"]!="queued":print(f"Job {job['id']} is {job['status']}; only queued jobs can be claimed.");continue
        if job["analysis_type"]!="three_bureau_credit_report":print(f"Skipped non-allowlisted analysis type for job {job['id']}");continue
        if job["attempt_count"]>=job["max_attempts"]:
            if not a.dry_run:request("PATCH",url,key,f"credit_analysis_jobs?id=eq.{job['id']}",{"status":"failed_permanent","retryable":False,"failure_code":"MAX_ATTEMPTS","failure_message":"Maximum bounded attempts reached."})
            failures+=1;continue
        if a.dry_run:print(f"DRY RUN: would claim job {job['id']} using parser {job['parser_version']}");continue
        lease=(datetime.now(timezone.utc)+timedelta(minutes=LEASE_MINUTES)).isoformat();claimed=request("PATCH",url,key,f"credit_analysis_jobs?id=eq.{job['id']}&status=eq.queued",{"status":"processing","claimed_at":now(),"claimed_by":worker_id,"lease_expires_at":lease,"started_at":now(),"attempt_count":job["attempt_count"]+1,"worker_version":WORKER_VERSION})
        if not claimed:print(f"Skipped already-claimed job {job['id']}");continue
        job=claimed[0];request("PATCH",url,key,f"credit_document_workflows?document_id=eq.{job['document_id']}",{"analysis_status":"processing"});event(url,key,job,"analysis_claimed",{"attempt":job["attempt_count"],"lease_minutes":LEASE_MINUTES})
        print(f"Processing bounded credit analysis job {job['id']} (attempt {job['attempt_count']}/{job['max_attempts']})")
        try:
            result=subprocess.run([sys.executable,"scripts/credit/parse_uploaded_credit_report.py","--document-id",job["document_id"],"--analysis-job-id",job["id"],"--out","reports/credit_repair/live_upload_parser_results"],cwd=Path(__file__).resolve().parents[2],check=False)
            if result.returncode!=0:raise RuntimeError(f"parser exited with code {result.returncode}")
            parser_rows=request("GET",url,key,f"credit_report_parser_results?analysis_job_id=eq.{job['id']}&extraction_success=eq.true&select=id&limit=1");review_rows=request("GET",url,key,f"credit_report_system_reviews?document_id=eq.{job['document_id']}&select=id&order=created_at.desc&limit=1")
            if not parser_rows or not review_rows:raise RuntimeError("verified parser result or system review missing")
            canonical=request("GET",url,key,f"credit_canonical_accounts?parser_result_id=eq.{parser_rows[0]['id']}&select=id");tradelines=request("GET",url,key,f"credit_bureau_tradelines?parser_result_id=eq.{parser_rows[0]['id']}&select=id")
            if not canonical or not tradelines:raise RuntimeError("canonical persistence verification failed")
            request("PATCH",url,key,f"credit_analysis_jobs?id=eq.{job['id']}&status=eq.processing",{"status":"complete","parser_result_id":parser_rows[0]["id"],"system_review_id":review_rows[0]["id"],"completed_at":now(),"lease_expires_at":None,"retryable":False,"failure_code":None,"failure_message":None});event(url,key,job,"analysis_completed",{"canonical_accounts":len(canonical),"bureau_tradelines":len(tradelines)})
            print(f"Analysis complete for job {job['id']}: {len(tradelines)} tradelines, {len(canonical)} canonical accounts")
        except Exception as error:
            failures+=1;summary=safe_failure(error,key);permanent="canonical persistence" in summary or "verification" in summary;retryable=not permanent and job["attempt_count"]<job["max_attempts"];status="failed_retryable" if retryable else "failed_permanent";code="RESULT_INTEGRITY_FAILURE" if permanent else "ANALYSIS_EXECUTION_FAILED"
            request("PATCH",url,key,f"credit_analysis_jobs?id=eq.{job['id']}",{"status":status,"retryable":retryable,"failure_code":code,"failure_message":summary,"completed_at":now(),"lease_expires_at":None});request("PATCH",url,key,f"credit_document_workflows?document_id=eq.{job['document_id']}",{"analysis_status":status,"exception_review_status":"required" if not retryable else "not_required","exception_code":code if not retryable else None,"exception_reason":"System processing requires attention." if not retryable else None});event(url,key,job,"analysis_failed",{"code":code,"retryable":retryable});print(f"Analysis failed for job {job['id']}: {summary}",file=sys.stderr)
    return 1 if failures else 0
if __name__=="__main__":raise SystemExit(main())
