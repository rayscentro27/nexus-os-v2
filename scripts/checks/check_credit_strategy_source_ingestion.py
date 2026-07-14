#!/usr/bin/env python3
import json,subprocess,sys
from pathlib import Path
r=Path(__file__).resolve().parents[2];fixture=r/"tests/fixtures/research/credit_coach_q_method_summary.json"
p=subprocess.run([sys.executable,str(r/"scripts/research/ingest_credit_strategy_source.py"),"--source-type","youtube","--input-file",str(fixture),"--title","fixture","--dry-run"],capture_output=True,text=True,check=True);d=json.loads(p.stdout)
assert d["strategy_leads"]==12 and d["rejected_promotional_claims"]==8 and d["status"]=="needs_verification"
print("PASS: practitioner source ingested as discovery, not authority")
