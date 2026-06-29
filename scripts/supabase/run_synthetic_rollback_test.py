#!/usr/bin/env python3
"""Gate a rollback test; skips remote writes when transaction rollback cannot be guaranteed."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import now,write_report  # noqa:E402
def build():
 report={"ok":True,"generated_at":now(),"status":"skipped_no_guaranteed_transaction_channel","test_attempted":False,"rollback_guaranteed":False,"persistent_record_created":False,"database_write_performed":False,"reason":"Supabase CLI provides schema inspection but no bounded transaction callback in this environment; a REST insert/delete pair is not equivalent to guaranteed rollback.","next_required_action":"Approve a server-side SQL function or direct transaction harness that always raises/rolls back synthetic test rows.","external_action_performed":False}
 write_report("synthetic_rollback_transaction_test","Synthetic Rollback Transaction Test",report);return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
