"""The live R16 source reconciliation accepts R10 qualified terminal results."""
from __future__ import annotations

import json
import os
import subprocess
import sqlite3
from pathlib import Path

R16 = Path.home() / ".nexus/releases/nexus-research-runtime-r10-automated-queue-20261104-r16"


def test_completed_with_limitations_reconciles_same_durable_job(tmp_path):
    script=r'''import json,sqlite3,sys
from pathlib import Path
from nexus_research_r10 import autonomy
from nexus_research_r10.batchc import JobStore,connection,digest
root=Path(sys.argv[1]); registry=root/"registry.sqlite3"; research=root/"research.sqlite3"
with sqlite3.connect(registry) as db:
 db.execute("CREATE TABLE youtube_channels(channel_id TEXT PRIMARY KEY,channel_name TEXT,enabled INTEGER,status TEXT,priority TEXT,updated_at TEXT)")
 db.execute("CREATE TABLE youtube_video_ingestions(video_id TEXT PRIMARY KEY,channel_id TEXT,job_id TEXT,observed_at TEXT,status TEXT,attempts INTEGER DEFAULT 0,next_attempt_at TEXT)")
job=JobStore(research).create("Bounded inconclusive Research",research_type="GENERAL",idempotency_key=digest("limited")); job.update(status="COMPLETED_WITH_LIMITATIONS",current_stage="COMPLETE_WITH_LIMITATIONS")
with connection(research) as db: db.execute("UPDATE jobs SET payload=?,updated_at=? WHERE job_id=?",(json.dumps(job),"2026-11-04T00:00:00+00:00",job["job_id"]))
with sqlite3.connect(root/"research_r10_bridge.sqlite3") as db:
 db.execute("CREATE TABLE bridge_results(job_id TEXT PRIMARY KEY,result_json TEXT NOT NULL,updated_at TEXT NOT NULL)"); db.execute("INSERT INTO bridge_results VALUES(?,?,?)",(job["job_id"],json.dumps({"status":"COMPLETED_WITH_LIMITATIONS"}),"2026-11-04"))
with sqlite3.connect(registry) as db: db.execute("INSERT INTO youtube_video_ingestions VALUES(?,?,?,?,?,?,?)",("vid","channel",job["job_id"],"2026-11-04","SUBMITTED",0,None))
called=[]; result=autonomy.reconcile_submitted_jobs(registry,research,lambda *args:called.append(args),"2026-11-04T01:00:00+00:00")
with sqlite3.connect(registry) as db: state,job_id=db.execute("SELECT status,job_id FROM youtube_video_ingestions").fetchone()
assert (state,job_id)==("COMPLETED",job["job_id"]); assert result["completed"]==1 and not called
'''
    env=dict(os.environ, PYTHONPATH=str(R16), PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    result=subprocess.run([str(Path.home()/".nexus/venvs/research-r10-20261027-batch-b/bin/python"),"-c",script,str(tmp_path)],env=env,capture_output=True,text=True,timeout=20)
    assert result.returncode==0, result.stderr or result.stdout
