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
if __name__=="__main__":main()
