#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import now,write_report  # noqa:E402
def build():
 rows=[
  {"blocker":"Stripe Checkout completion","status":"blocked_by_approval","cause":"Browser test payment not completed","fix_attempted":"Test Checkout created and status tracked","result":"open_unpaid","next_action":"Approve manual test Checkout completion"},
  {"blocker":"Stripe PaymentIntent confirmation","status":"blocked_by_approval","cause":"Test payment method not approved","fix_attempted":"Test intent created and reusable","result":"requires_payment_method","next_action":"Approve pm_card_visa test confirmation"},
  {"blocker":"Resend","status":"blocked_by_missing_credential","cause":"Key/account permission and .cc/.com sender mismatch","fix_attempted":"Read-only diagnosis and fix packet","result":"HTTP 403","next_action":"Verify goclearonline.com and replace/re-scope key"},
  {"blocker":"Persistent fake customer","status":"blocked_by_approval","cause":"Production write intentionally gated","fix_attempted":"RLS verified; insert/cleanup packets ready","result":"ready_for_Ray_approval","next_action":"Approve explicit synthetic insert"},
  {"blocker":"Frontend live data","status":"blocked_by_approval","cause":"Fake customer not persistently inserted","fix_attempted":"Flagged live-read service with fallback","result":"implementation_ready_flag_off","next_action":"Enable after insert verification"},
  {"blocker":"YouTube transcript","status":"blocked_by_missing_source","cause":"Approved TXT absent","fix_attempted":"Approved dropzone and import packet","result":"metadata_review_active","next_action":"Add zbAmmnMh5ew.txt"},
  {"blocker":"NotebookLM import","status":"blocked_by_missing_source","cause":"No approved export file","fix_attempted":"Legacy adapter and dropzone recovered","result":"zero_sources","next_action":"Add selected notebook export"},
  {"blocker":"Oanda practice verification","status":"blocked_by_missing_credential","cause":"Practice environment not explicit","fix_attempted":"Read-only guard and plan","result":"no API call","next_action":"Set OANDA_ENVIRONMENT=practice"},
  {"blocker":"Vibe CLI","status":"partially_completed","cause":"CLI package unidentified","fix_attempted":"Recovered legacy synthetic backtest","result":"50-trade backtest passed","next_action":"Do not install until trusted package is identified"},
  {"blocker":"Permanent schedule","status":"blocked_by_approval","cause":"Permanent daemon requires approval","fix_attempted":"Validated launchd install/rollback plan","result":"not installed","next_action":"Approve safe scheduler installation"},
 ]
 report={"ok":True,"generated_at":now(),"status":"global_blocker_matrix_ready","blockers_total":len(rows),"resolved_or_partially_resolved":sum(x["status"]=="partially_completed" for x in rows),"approval_gated":sum(x["status"]=="blocked_by_approval" for x in rows),"missing_source":sum(x["status"]=="blocked_by_missing_source" for x in rows),"missing_credential":sum(x["status"]=="blocked_by_missing_credential" for x in rows),"external_action_performed":False,"blockers":rows};write_report("global_blocker_resolution_matrix","Global Blocker Resolution Matrix",report,{"Blockers":rows});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
