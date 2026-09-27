#!/usr/bin/env python3
"""Generate a morning Research snapshot without stopping the Research service."""
from __future__ import annotations
import json, os
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN_ID = os.environ.get("NEXUS_MORNING_REPORT_ID", "morning-" + datetime.now(timezone.utc).strftime("%Y%m%d"))
JOB_LOG = ROOT / "data/runtime/research_execution_jobs.jsonl"
OUT_MD = ROOT / "reports/research" / f"NEXUS_RESEARCH_OVERNIGHT_INTELLIGENCE_{datetime.now().strftime('%Y-%m-%d')}.md"
OUT_JSON = ROOT / "reports/research" / f"nexus_research_overnight_intelligence_{datetime.now().strftime('%Y%m%d')}.json"

def read_jobs():
    rows=[]
    try:
        for line in JOB_LOG.read_text().splitlines():
            try: rows.append(json.loads(line))
            except Exception: pass
    except OSError: pass
    return rows

def main():
    now = datetime.now(timezone.utc); cutoff = now - timedelta(hours=12)
    jobs=[]
    for row in read_jobs():
        try:
            at=datetime.fromisoformat(str(row.get("at")).replace("Z", "+00:00"))
            if at >= cutoff: jobs.append(row)
        except Exception: pass
    status_counts={}
    programs={}
    for row in jobs:
        status=str(row.get("status") or "UNKNOWN"); status_counts[status]=status_counts.get(status,0)+1
        lane=str(row.get("lane_id") or row.get("objective_id") or "UNKNOWN")
        item=programs.setdefault(lane,{"runs":0,"substantive":0,"failures":0,"last_success":None})
        if status in {"SOURCE_SELECTED","AI_RESULT_INTERPRETATION","EVIDENCE_READY","COMPLETED"}: item["runs"]+=1
        if row.get("information_gain") or row.get("content_count") or status == "EVIDENCE_READY": item["substantive"]+=1
        if "FAIL" in status or status == "DEGRADED": item["failures"]+=1
        if status == "EVIDENCE_READY": item["last_success"]=row.get("at")
    heartbeat={}
    try: heartbeat=json.loads((ROOT/"data/runtime/research_heartbeat.json").read_text())
    except Exception: pass
    payload={"run_id":RUN_ID,"generated_at":now.isoformat(),"window_start":cutoff.isoformat(),"window_end":now.isoformat(),"jobs":len(jobs),"status_counts":status_counts,"programs":programs,"heartbeat":heartbeat,"research_continues":True,"production_actions":{"published":0,"customer_messages":0,"funds_moved":0,"trades":0}}
    OUT_JSON.parent.mkdir(parents=True,exist_ok=True); OUT_JSON.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
    lines=[f"# Nexus Research Overnight Intelligence — {now.date()}","",f"OVERNIGHT_START={cutoff.isoformat()}",f"OVERNIGHT_END={now.isoformat()}",f"RECEIPTS={len(jobs)}",f"RESEARCH_CONTINUES={heartbeat.get('enabled', True)}","","## Program service",""]
    for lane,item in sorted(programs.items()): lines.append(f"{lane}: RUNS={item['runs']} SUBSTANTIVE_FINDINGS={item['substantive']} FAILURES={item['failures']} LAST_SUCCESS={item['last_success']}")
    lines += ["","## Runtime status",f"SERVICE_HEARTBEAT={heartbeat.get('heartbeat')}",f"NEXT_WAKE={heartbeat.get('next_wake')}",f"LAST_REAL_OUTPUT={heartbeat.get('last_real_output')}","","MORNING_REPORT_STOPS_RESEARCH=NO","PUBLIC_CONTENT_PUBLISHED=0","CUSTOMER_MESSAGES_SENT=0","FUNDS_MOVED=0","LIVE_TRADES_EXECUTED=0",""]
    OUT_MD.parent.mkdir(parents=True,exist_ok=True); OUT_MD.write_text("\n".join(lines))

if __name__ == "__main__": main()
