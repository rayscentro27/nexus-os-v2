#!/usr/bin/env python3
"""Process a bounded number of queued credit research sources; never auto-approve."""
from __future__ import annotations
import argparse, json, sys
from ingest_credit_strategy_source import env, request
def main():
    p=argparse.ArgumentParser();p.add_argument("--once",action="store_true");p.add_argument("--max-items",type=int,default=1);a=p.parse_args();limit=1 if a.once else max(1,min(a.max_items,10));e=env();url=e.get("SUPABASE_URL");key=e.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:print("ERROR: server-side environment required.",file=sys.stderr);return 1
    rows=request("GET",url,key,f"credit_strategy_sources?review_status=eq.queued&select=id,title&order=created_at.asc&limit={limit}");processed=0
    for row in rows:
        claimed=request("PATCH",url,key,f"credit_strategy_sources?id=eq.{row['id']}&review_status=eq.queued",{"review_status":"processing"})
        if not claimed:continue
        request("PATCH",url,key,f"credit_strategy_sources?id=eq.{row['id']}",{"review_status":"needs_verification"});processed+=1
    print(json.dumps({"processed":processed,"bounded_limit":limit,"auto_approved":False}));return 0
if __name__=="__main__":raise SystemExit(main())
