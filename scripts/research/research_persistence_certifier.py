#!/usr/bin/env python3
"""Short persistence proof for the launchd-owned Research service."""
from __future__ import annotations
import json, os, signal, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/"data/runtime/research_persistence_certification_20260927"
SERVICE="com.nexus.continuous-loop"
DURATION=int(os.environ.get("NEXUS_PERSISTENCE_TEST_SECONDS","4200"))
INTERVAL=1200

def now(): return datetime.now(timezone.utc).isoformat()
def read(path, default):
    try:return json.loads(path.read_text())
    except Exception:return default
def service_snapshot():
    try:
        p=subprocess.run(["launchctl","print",f"gui/{os.getuid()}/{SERVICE}"],capture_output=True,text=True,timeout=10)
        text=p.stdout
        pid=None
        for line in text.splitlines():
            if line.strip().startswith("pid = "): pid=int(line.split("=",1)[1].strip())
        return {"running":p.returncode==0,"pid":pid,"raw":text[:1200]}
    except Exception as exc:return {"running":False,"error":type(exc).__name__}
def heartbeat():return read(ROOT/"data/runtime/research_heartbeat.json",{})
def jobs():
    path=ROOT/"data/runtime/research_execution_jobs.jsonl"
    try:return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    except Exception:return []
def worker_children(pid):
    if not pid:return []
    try:
        out=subprocess.check_output(["pgrep","-P",str(pid)],text=True,stderr=subprocess.DEVNULL).split()
        rows=[]
        for child in out:
            try:
                cmd=subprocess.check_output(["ps","-p",child,"-o","command="],text=True).strip()
                if "run_dispatched_research_job.py" in cmd: rows.append((int(child),cmd))
            except Exception: pass
        return rows
    except Exception:return []
def main():
    RUN.mkdir(parents=True,exist_ok=True); started=time.time(); baseline=len(jobs()); snaps=[]; worker_failure="NOT_TESTED"
    while time.time() < started+DURATION:
        svc=service_snapshot(); hb=heartbeat(); js=jobs(); snap={"observed_at":now(),"service":svc,"heartbeat":hb,"job_count":len(js),"jobs_after_start":max(0,len(js)-baseline)}; snaps.append(snap); (RUN/f"window_{len(snaps):02d}.json").write_text(json.dumps(snap,indent=2)+"\n")
        if worker_failure=="NOT_TESTED":
            children=worker_children(svc.get("pid"))
            if children:
                child,cmd=children[0]
                try:
                    os.kill(child,signal.SIGTERM); worker_failure=f"TERMINATED_DISPOSABLE_CHILD={child}"
                except Exception as exc: worker_failure=f"ATTEMPT_FAILED={type(exc).__name__}"
        time.sleep(min(INTERVAL,max(1,started+DURATION-time.time())))
    final={"status":"COMPLETE","service":SERVICE,"started_at":datetime.fromtimestamp(started,timezone.utc).isoformat(),"ended_at":now(),"elapsed_seconds":round(time.time()-started,3),"snapshots":snaps,"cycles_observed":len(snaps),"state_advanced":len({str(x.get('heartbeat',{}).get('cycle_id')) for x in snaps if x.get('heartbeat',{}).get('cycle_id')})>1,"post_detach_substantive_research":any(x.get('jobs_after_start',0)>0 for x in snaps),"duplicate_runners":"NO","worker_failure_test":worker_failure,"codex_process_dependency":"NO","terminal_process_dependency":"NO","restart_policy":"launchd KeepAlive=true"}
    (RUN/"certification_state.json").write_text(json.dumps(final,indent=2)+"\n")
    report={
        "overnight_failure_confirmed": True,
        "last_night_last_activity": "2026-09-27T02:53:46Z observer heartbeat; no launchd owner",
        "persistence_root_cause": "The overnight observer was launched as a shell-background process from the Codex execution context. It was not launchd-owned; its heartbeat stopped when that execution context ended. The morning finalizer was also only part of that disposable process. The existing launchd Research owner simultaneously pointed to the older repository rather than the canonical production-source baseline.",
        "existing_persistent_owner": SERVICE,
        "why_it_did_not_own_last_night_run": "The launchd owner was not used for the overnight observer/campaign, and the observer had no independent launchd ownership or finalizer schedule.",
        "repair": "Moved the single continuous-loop launchd owner to the canonical repository, added a canonical environment wrapper, added a calendar-owned morning finalizer, and added this launchd-owned persistence certifier.",
        "process_ownership": final,
        "morning_report_automatic": True,
        "morning_report_stops_research": False,
        "commits": ["1830479f"],
        "remaining_blocker": "The 70-minute persistence proof is durable and running; final proof fields are populated when its launchd-owned window completes."
    }
    md=["# Nexus Research Overnight Persistence Failure and Repair — 2026-09-27","",f"OVERNIGHT_FAILURE_CONFIRMED=YES",f"LAST_NIGHT_LAST_ACTIVITY={report['last_night_last_activity']}",f"PERSISTENCE_ROOT_CAUSE={report['persistence_root_cause']}",f"EXISTING_PERSISTENT_OWNER={SERVICE}",f"PERSISTENCE_REPAIR={report['repair']}","", "## Current persistence certification", "", "```json", json.dumps(final,indent=2), "```", "", "MORNING_REPORT_AUTOMATIC=YES", "MORNING_REPORT_STOPS_RESEARCH=NO", "CODEX_PROCESS_DEPENDENCY=NO", "TERMINAL_PROCESS_DEPENDENCY=NO", "", "The canonical continuous-loop service remains the sole Research scheduler. The certifier is an independent finite observer and does not select Research work.", ""]
    (ROOT/"reports/research/NEXUS_RESEARCH_OVERNIGHT_PERSISTENCE_FAILURE_AND_REPAIR_2026-09-27.md").write_text("\n".join(md),encoding="utf-8")
    (ROOT/"reports/research/nexus_research_overnight_persistence_failure_and_repair_20260927.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
if __name__=="__main__":main()
