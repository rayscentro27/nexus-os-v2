#!/usr/bin/env python3
"""Bounded, read-only Nova release certification; never sends Telegram or creates work."""
from __future__ import annotations

import os
import base64
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORACLE = "opc@161.153.40.41"
SSH = ["ssh", "-i", str(Path.home() / ".ssh/oracle_vm"), "-o", "BatchMode=yes",
       "-o", "ConnectTimeout=8", "-o", "StrictHostKeyChecking=accept-new", ORACLE]
R25 = "/home/opc/.nexus/releases/nova-operator-v1-20261020-r25"
ACTIVE_NOVA_RELEASE = os.environ.get("NOVA_ACTIVE_RELEASE", R25)
OLD_RESEARCH_R3 = "/Users/raymonddavis/.nexus/releases/nexus-research-runtime-plan-assigned-work-20261019-r3"
RESEARCH_ACTIVE = "/Users/raymonddavis/.nexus/releases/nexus-research-runtime-isolated-closure-20261020-r3"
EXPECTED = {
    "nova_telegram_worker.py": "fed03c019c386318677e9cefd2263453e5d2f80da4933891589ce250d2be1761",
    "operator_v1.py": "44324fa7b28674056d2ea6051a0f804ccfdd0c694b25b1b50d2894d66d742bda",
}


def run(name: str, command: list[str], *, input_text: str | None = None,
        env: dict[str, str] | None = None, timeout_seconds: int = 90) -> tuple[bool, str]:
    try:
        result = subprocess.run(command, input=input_text, capture_output=True, text=True,
                                timeout=timeout_seconds, env=env, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"{name}=FAIL ({type(exc).__name__})"
    output = (result.stdout + "\n" + result.stderr).strip()
    return result.returncode == 0, output


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    expected_hash_lines = "\n".join(
        f"test \"$(sha256sum {R25}/scripts/nova/{name} | awk '{{print $1}}')\" = {digest}"
        for name, digest in EXPECTED.items())
    protected_hash_command = f'''set -eu
test -d {R25}
{expected_hash_lines}
cd {R25}
sha256sum -c RELEASE_MANIFEST.sha256 >/dev/null
printf 'R25_PROTECTED_HASHES=PASS RELEASE_MANIFEST=PASS\\n'
'''
    protected_ok, protected_out = run("PROTECTED_R25", SSH + [protected_hash_command])
    checks.append(("PROTECTED_R25_HASHES", protected_ok, protected_out))

    env = os.environ.copy()
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYDANTIC_DISABLE_PLUGINS"] = "1"
    env["PYTHONPATH"] = str(ROOT / "scripts") + os.pathsep + env.get("PYTHONPATH", "")
    test_python = ROOT / ".venv-agent-platform/bin/python"
    if not test_python.is_file():
        test_python = Path(sys.executable)
    ok, out = run("CONTRACT_TESTS", [str(test_python), "-m", "pytest",
                 "scripts/nova/tests/test_r25_baseline_contracts.py",
                 "scripts/nova/tests/test_operator_shadow.py",
                 "scripts/nova/tests/test_operator_phase2_contracts.py",
                 "scripts/nova/tests/test_wave2_workspace_adapter.py",
                 "scripts/nova/tests/test_wave2_crud_planning.py",
                 "scripts/nova/tests/test_wave3_case_resolution.py",
                 "scripts/nova/tests/test_operator_v1.py::test_d_file_artifact_readback_verifies_without_receipt",
                 "-q", "--tb=short"], env=env, timeout_seconds=180)
    checks.append(("FOCUSED_CONTRACT_TESTS", ok, out.splitlines()[-1] if out else "no test output"))

    poller_command = r'''set -eu
test "$(systemctl --user is-active nova-telegram-oracle.service)" = active
test "$(systemctl --user is-enabled nova-telegram-oracle.service)" = enabled
pid=$(systemctl --user show nova-telegram-oracle.service -p MainPID --value)
test -n "$pid" -a "$pid" != 0
cmd=$(tr "\0" " " </proc/$pid/cmdline)
case "$cmd" in *__ACTIVE_RELEASE__/scripts/nova/nova_telegram_worker.py*--poll*) ;; *) exit 11 ;; esac
count=$(ps -eo args | awk '$1 ~ /python/ && $0 ~ /nova_telegram_worker[.]py/ && $0 ~ /--poll/ {n++} END {print n+0}')
test "$count" = 1
offset_file=/home/opc/nexus-os-v2-source/data/runtime/nova_telegram_last_update_id.json
test -r "$offset_file"
offset=$(python3 -c "import json; print(json.load(open('$offset_file')).get('last_update_id', 'UNKNOWN'))")
offset_at=$(python3 -c "import json; print(json.load(open('$offset_file')).get('updated_at', 'UNKNOWN'))")
cd __ACTIVE_RELEASE__
sha256sum -c RELEASE_MANIFEST.sha256 >/dev/null
mode_file=/home/opc/.config/nova-operator-routing-mode.json
current_mode=$(python3 -c "import json; print(json.load(open('$mode_file')).get('routes',{}).get('R24.current',''))")
completed_mode=$(python3 -c "import json; print(json.load(open('$mode_file')).get('routes',{}).get('R24.last_completed',''))")
test "$current_mode" = CANONICAL
test "$completed_mode" = CANONICAL
printf 'POLLERS=%s PID=%s RELEASE=__ACTIVE_RELEASE__ MANIFEST=PASS OFFSET=%s OFFSET_LAST_ADVANCED_AT=%s\n' "$count" "$pid" "$offset" "$offset_at"
printf 'WAVE1_MODES=PASS R24.current=%s R24.last_completed=%s\n' "$current_mode" "$completed_mode"
'''.replace("__ACTIVE_RELEASE__", ACTIVE_NOVA_RELEASE)
    ok, out = run("LIVE_NOVA", SSH + [poller_command])
    checks.append(("LIVE_NOVA_POLL_AND_HASH", ok, out))
    checks.append(("POLLER_HISTORICAL_OFFSET_EVIDENCE", ok and "OFFSET=" in out,
                   "live unit/uniqueness verified; offset timestamp recorded; no synthetic Telegram update used"))

    live_read_probe = r'''import json,sqlite3,os
from nova.operator_v1 import status_read,store_path,_read_only_connect,recent_completed_status,get_authoritative_mission_snapshot
db_path=store_path(); db=_read_only_connect(); assert db is not None
owners=[str(x[0]) for x in db.execute("SELECT DISTINCT owner_id FROM operator_missions")]; db.close()
states=[status_read(owner_id=owner) for owner in owners]
assert states and all(x and x.get("read_only") and x.get("no_mutation") for x in states)
assert any(x.get("status")=="NO_ACTIVE_MISSION" for x in states)
print("MISSION_SNAPSHOT=PASS NO_ACTIVE_MISSION=YES READ_ONLY=YES")
owner="1288928049"; mission_id="nova_20261019T145014_590357499"
active=status_read(None,owner_id=owner); last=recent_completed_status(owner)
final=get_authoritative_mission_snapshot(mission_id,owner_id=owner)
assert active and active.get("status")=="NO_ACTIVE_MISSION"
assert last and last.get("status")=="COMPLETE" and last.get("success_verified")
assert final and final.get("status")=="COMPLETE" and final.get("success_verified")
db=_read_only_connect(); events=db.execute("SELECT event_type,payload_json FROM operator_events WHERE mission_id=?",(mission_id,)).fetchall(); db.close()
historical=[(row["event_type"],json.loads(row["payload_json"] or "{}")) for row in events]
assert any(name=="MISSION_BLOCKED_TRUE" and payload.get("blocker_type")=="TRUE_TECHNICAL_BLOCKER" for name,payload in historical)
assert any(event.get("event_type")=="MISSION_BLOCKED_TRUE" for event in final.get("historical_problem_events",[]))
print("WAVE1_HISTORICAL_FIXTURES=PASS CURRENT=NO_ACTIVE_MISSION LAST=COMPLETE TECHNICAL_BOUNDARY=HISTORICAL_ONLY")
for key in ("NOVA_RUNTIME_ENV","NEXUS_GOVERNOR_DB","NEXUS_HERMES_TRANSPORT","NOVA_CODE_ROOT","NEXUS_REPO_ROOT"):
 assert os.environ.get(key),"MISSING_RUNTIME_KEY:"+key
assert os.path.isfile(os.environ["NOVA_RUNTIME_ENV"])
assert os.path.isfile(os.environ["NEXUS_GOVERNOR_DB"])
print("RUNTIME_ENV=PASS DB_PATHS=PASS SECRETS=NOT_PRINTED")
from nova.approved_mcp_registry import discover_approved_mcp
catalog=discover_approved_mcp(force=True)
assert not catalog.get("error") and len(catalog.get("tools") or [])>0
print("CAPABILITY_CATALOG=PASS TOOLS="+str(len(catalog.get("tools") or [])))
'''
    remote_probe = r'''import base64,os,subprocess,sys
pid=subprocess.check_output(["systemctl","--user","show","nova-telegram-oracle.service","-p","MainPID","--value"],text=True).strip()
env={}
for row in open("/proc/"+pid+"/environ","rb").read().split(b"\0"):
 if b"=" in row:
  k,v=row.split(b"=",1); env[k.decode()]=v.decode(errors="replace")
env["PYTHONPATH"]="__ACTIVE_RELEASE__/scripts"
env["PYTHONDONTWRITEBYTECODE"]="1"
code=base64.b64decode("__CODE__").decode()
p=subprocess.run([sys.executable,"-c",code],env=env,capture_output=True,text=True,timeout=100)
print(p.stdout,end=""); print(p.stderr[-1200:],file=sys.stderr,end="")
raise SystemExit(p.returncode)
'''.replace("__ACTIVE_RELEASE__", ACTIVE_NOVA_RELEASE)
    remote_probe = remote_probe.replace("__CODE__", base64.b64encode(live_read_probe.encode()).decode())
    ok, out = run("LIVE_NOVA_READ_ONLY_STATE", SSH + ["python3 -c '" + remote_probe + "'"])
    checks.append(("LIVE_RUNTIME_STATE_ENV_AND_CAPABILITY_CATALOG", ok, out))

    validator_python = "/home/opc/.local/share/nexus-venvs/nova-runtime/bin/python"
    remote_validator = "/tmp/validate_nova_release-r25-cert.py"
    copy_ok, copy_out = run("COPY_R25_VALIDATOR", ["scp", "-i", str(Path.home() / ".ssh/oracle_vm"),
        "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", "-o", "StrictHostKeyChecking=accept-new",
        str(ROOT / "scripts/ops/validate_nova_release.py"), f"{ORACLE}:{remote_validator}"])
    if copy_ok:
        ok, out = run("R25_RELEASE_CLOSURE", SSH + [
            f"PYTHONDONTWRITEBYTECODE=1 {validator_python} {remote_validator} {R25}"])
    else:
        ok, out = False, copy_out
    checks.append(("R25_RELEASE_DEPENDENCIES", ok, out))

    if ACTIVE_NOVA_RELEASE != R25:
        ok, out = run("ACTIVE_NOVA_RELEASE_CLOSURE", SSH + [
            f"PYTHONDONTWRITEBYTECODE=1 {validator_python} {remote_validator} {ACTIVE_NOVA_RELEASE}"])
        checks.append(("ACTIVE_NOVA_RELEASE_DEPENDENCIES", ok, out))

    research_command = [str(test_python), "scripts/ops/validate_nova_release.py", RESEARCH_ACTIVE,
                        "--entrypoint", "scripts/nexus_agent_platform/dispatcher_once.py",
                        "--entrypoint", "scripts/nexus_agent_platform/job_worker_once.py",
                        "--entrypoint", "scripts/research/run_dispatched_research_job.py",
                        "--reachable-import-closure", "--source-root", str(ROOT),
                        "--active-release", OLD_RESEARCH_R3,
                        "--canonical-source-root", str(ROOT),
                        "--module", "nexus_agent_platform.research_assignment_executor",
                        "--module", "research.research_case_engine",
                        "--module", "research.company_case_contracts",
                        "--module", "nexus_agent_platform.notebooklm_discovery",
                        "--module", "nexus_agent_platform.real_world_v2_workflow",
                        "--module", "nexus_agent_platform.v5_owner_workflow",
                        "--module", "research.youtube_channel_registry",
                        "--symbol", "nexus_agent_platform.research_ai_orchestrator:plan_assigned_work"]
    ok, out = run("ACTIVE_RESEARCH_RELEASE_CLOSURE", research_command, env=env)
    checks.append(("ACTIVE_RESEARCH_RELEASE_DEPENDENCIES", ok, out))

    equivalence = [str(test_python), "scripts/ops/certify_research_read_only_equivalence.py",
                   "--active-release", OLD_RESEARCH_R3, "--candidate-release", RESEARCH_ACTIVE,
                   "--case-id", "rcase_80fb1ea338bfaa1b41"]
    ok, out = run("RESEARCH_READ_ONLY_EQUIVALENCE", equivalence, env=env)
    checks.append(("RESEARCH_READ_ONLY_CASE_EQUIVALENCE", ok and "RESEARCH_BEHAVIORAL_EQUIVALENCE=PASS" in out, out))

    keychain = subprocess.run(["/usr/bin/security", "find-generic-password", "-s",
        "nexus/credential.nexus.mcp.bridge.v1", "-a", "bridge_token", "-w"],
        capture_output=True, text=True, check=False)
    mcp_env = env.copy()
    if keychain.returncode == 0 and keychain.stdout.strip():
        mcp_env["NEXUS_MCP_BRIDGE_TOKEN"] = keychain.stdout.strip()
    mcp_probe = r'''import asyncio,json,os,httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
async def main():
 async with httpx.AsyncClient(headers={"Authorization":"Bearer "+os.environ["NEXUS_MCP_BRIDGE_TOKEN"]},timeout=15) as c:
  async with streamable_http_client("http://127.0.0.1:18765/mcp",http_client=c) as streams:
   rd,wr=streams[:2]
   async with ClientSession(rd,wr) as s:
    await s.initialize(); tools=await s.list_tools(); print("MCP_TOOL_COUNT="+str(len(tools.tools))); assert len(tools.tools)>=42
asyncio.run(main())'''
    ok, out = (run("LOCAL_MCP", [str(test_python), "-c", mcp_probe], env=mcp_env)
               if "NEXUS_MCP_BRIDGE_TOKEN" in mcp_env else (False, "keychain credential unavailable"))
    checks.append(("LOCAL_MCP_INITIALIZE_AND_LIST", ok, out))

    health_command = r'''set -eu
podman exec nexus-hermes-0206 /opt/hermes/.venv/bin/hermes --profile nova_nexus mcp test nexus_mcp_remote 2>&1 | grep -E 'Connected|Tools discovered'
'''
    ok, out = run("ORACLE_MCP", SSH + [health_command])
    tool_count = re.search(r"Tools discovered:\s*(\d+)", out)
    checks.append(("ORACLE_MCP_INITIALIZE_AND_LIST", ok and bool(tool_count) and int(tool_count.group(1)) >= 42, out))

    local_port = subprocess.run(["/usr/sbin/lsof", "-nP", "-iTCP:18765", "-sTCP:LISTEN"],
                                capture_output=True, text=True, check=False)
    checks.append(("LOCAL_MCP_PORT", local_port.returncode == 0 and "127.0.0.1:18765" in local_port.stdout,
                   "127.0.0.1:18765 listening" if local_port.returncode == 0 else "port not listening"))

    failures = 0
    for name, passed, detail in checks:
        state = "PASS" if passed else "FAIL"
        print(f"{name}={state} {detail.replace(chr(10), ' | ')}")
        failures += not passed
    print("LIVE_TELEGRAM_SEND=NOT_RUN")
    print("LIVE_RESEARCH_JOB_CREATE=NOT_RUN")
    print(f"BASELINE_CERTIFICATION={'PASS' if failures == 0 else 'FAIL'}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
