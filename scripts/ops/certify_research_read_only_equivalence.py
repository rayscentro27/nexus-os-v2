#!/usr/bin/env python3
"""Compare the active and staged Research read paths without writes."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

PYTHON = Path(".venv-agent-platform/bin/python3")
READ_PROBE = r'''import inspect,json,sys
from research import research_case_engine as engine
from nexus_agent_platform import research_assignment_executor as assignment
from nexus_agent_platform import durable_jobs
from nexus_agent_platform import job_worker_once
case_id=sys.argv[1]
client=engine.research_memory.supabase
original=getattr(client,"rest",None) if client is not None else None
methods=[]
if original:
    def guarded(method,*args,**kwargs):
        methods.append(str(method).upper())
        if str(method).upper()!="GET": raise RuntimeError("read-only equivalence rejected non-GET request")
        return original(method,*args,**kwargs)
    client.rest=guarded
case=engine.get_case(case_id)
if case is None: raise SystemExit("CASE_NOT_FOUND")
questions=case.get("open_questions") or []
sources=case.get("sources") or []
syntheses=case.get("syntheses") or case.get("synthesis") or []
recommendations=case.get("recommendations") or []
recommendation=case.get("final_recommendation") or ((recommendations[-1].get("recommendation") if recommendations else None))
summary={
 "case_id":str(case.get("case_id") or case_id),"status":case.get("status"),
 "final_recommendation":recommendation,"source_count":int(case.get("source_count") or len(sources)),
 "synthesis_count":int(case.get("synthesis_count") or len(syntheses)),
 "open_question_count":len(questions),"read_methods":methods,
 "assignment_signature":str(inspect.signature(assignment.execute_assignment)),
 "dispatcher_signature":str(inspect.signature(durable_jobs.dispatch_once)),
 "claim_signature":str(inspect.signature(durable_jobs.SupabaseJobStore.claim)),
 "worker_signature":str(inspect.signature(job_worker_once.main)),
}
print(json.dumps(summary,sort_keys=True,separators=(",",":")))
'''


def read_summary(release: Path, case_id: str) -> dict:
    wrapper = release / "scripts/ops/run_with_canonical_runtime_env.sh"
    proc = subprocess.run([str(wrapper), str(PYTHON.resolve()), "-c", READ_PROBE, case_id],
                          cwd=release, capture_output=True, text=True, timeout=90, check=False)
    if proc.returncode:
        raise RuntimeError(f"READ_PROBE_FAILED release={release.name} rc={proc.returncode} stderr={proc.stderr[-1000:]}")
    lines = [line for line in proc.stdout.splitlines() if line.startswith("{")]
    if not lines: raise RuntimeError(f"READ_PROBE_NO_RESULT release={release.name}")
    value = json.loads(lines[-1])
    value["release"] = release.name
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--active-release", type=Path, required=True)
    parser.add_argument("--candidate-release", type=Path, required=True)
    parser.add_argument("--case-id", required=True)
    args = parser.parse_args()
    active = read_summary(args.active_release.resolve(), args.case_id)
    candidate = read_summary(args.candidate_release.resolve(), args.case_id)
    comparable = {key: value for key, value in active.items() if key != "release"}
    candidate_comparable = {key: value for key, value in candidate.items() if key != "release"}
    print("ACTIVE_BEHAVIOR=" + json.dumps(active, sort_keys=True))
    print("CANDIDATE_BEHAVIOR=" + json.dumps(candidate, sort_keys=True))
    same = comparable == candidate_comparable
    print(f"RESEARCH_BEHAVIORAL_EQUIVALENCE={'PASS' if same else 'FAIL'}")
    print("NO_NON_GET_REQUESTS=" + ("YES" if not any(method != "GET" for method in active["read_methods"] + candidate["read_methods"]) else "NO"))
    return 0 if same else 1


if __name__ == "__main__":
    raise SystemExit(main())
