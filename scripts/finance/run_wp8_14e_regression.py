"""Stable, sequential WP8.14E phase certification runner.

Each named phase gets an independent subprocess, bounded timeout, captured
output, and a durable receipt. A slow child cannot erase prior phase evidence.
"""
from __future__ import annotations
import json, os, signal, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports" / "rebuild" / "wp8_14e_regression_matrix.json"
EVIDENCE = ROOT / "reports" / "rebuild" / "wp8_14e_regression_output"
PY = sys.executable

GROUPS = {
    "WP8.6": ["scripts/nexus_foundation/tests/test_oanda_practice_engine.py", "scripts/nexus_foundation/tests/test_multi_market_lab.py"],
    "WP8.7": ["scripts/nexus_foundation/tests/test_business_opportunity_loop.py", "scripts/nexus_foundation/tests/test_business_loop.py"],
    "WP8.8": ["scripts/nexus_agent_platform/tests/test_opportunity_engine.py", "scripts/nexus_agent_platform/tests/test_business_loops.py"],
    "WP8.9": ["scripts/nexus_foundation/tests/test_growth_validation_loop.py", "scripts/nexus_agent_platform/tests/test_growth_operations.py"],
    "WP8.10": ["scripts/nexus_foundation/tests/test_adaptive_improvement_loop.py", "scripts/nexus_agent_platform/tests/test_learning_engine.py"],
    "WP8.11B": ["scripts/nexus_agent_platform/tests/test_creative_lab.py"],
    "WP8.11C": ["scripts/nexus_agent_platform/tests/test_creative_department.py", "-k", "territories or distinctiveness"],
    "WP8.11D": ["scripts/nexus_agent_platform/tests/test_creative_lab.py"],
    "WP8.11E": ["scripts/nexus_agent_platform/tests/test_governed_ops.py"],
    "WP8.12": ["scripts/nexus_agent_platform/tests/test_governed_ops.py", "scripts/nexus_agent_platform/tests/test_active_operator_v1_contract.py"],
    "WP8.13": ["scripts/nexus_agent_platform/tests/test_governed_ops.py", "scripts/nexus_agent_platform/tests/test_client_count.py"],
    "WP8.14": ["scripts/nexus_agent_platform/finance/tests/test_engine.py"],
    "WP8.14B": ["scripts/nexus_agent_platform/finance/tests/test_engine.py", "scripts/nexus_agent_platform/tests/test_governed_ops.py"],
    "WP8.14C": ["scripts/nexus_agent_platform/finance/tests/test_engine.py", "scripts/nexus_agent_platform/tests/test_governed_ops.py"],
    "WP8.14D": ["tests/e2e/wp8-14d-operator-finance.spec.ts"],
}

def now() -> str: return datetime.now(timezone.utc).isoformat()

def command_for(phase: str) -> tuple[list[str], dict[str, str]]:
    if phase == "WP8.14D":
        return ["npx", "playwright", "test", "tests/e2e/wp8-14d-operator-finance.spec.ts", "--timeout=15000", "--reporter=line"], {"E2E_BASE_URL": os.environ.get("E2E_BASE_URL", "http://127.0.0.1:4173")}
    return [PY, "-m", "pytest", "-q", *GROUPS[phase]], {}

def run_phase(phase: str, timeout_seconds: int = 90) -> dict:
    cmd, extra_env = command_for(phase); started = time.monotonic(); start = now()
    EVIDENCE.mkdir(parents=True, exist_ok=True); out_path = EVIDENCE / f"{phase.lower().replace('.', '_')}.stdout.log"; err_path = EVIDENCE / f"{phase.lower().replace('.', '_')}.stderr.log"
    env = {**os.environ, **extra_env, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTHONPATH": str(ROOT / "scripts")}
    child = subprocess.Popen(cmd, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    try:
        stdout, stderr = child.communicate(timeout=timeout_seconds)
        timed_out = False; exit_code = child.returncode
    except subprocess.TimeoutExpired as exc:
        os.killpg(child.pid, signal.SIGKILL)
        stdout, stderr = child.communicate()
        prior_stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        prior_stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        stdout = prior_stdout + stdout; stderr = prior_stderr + stderr
        timed_out = True; exit_code = None
    stdout, stderr = str(stdout), str(stderr)
    out_path.write_text(stdout); err_path.write_text(stderr)
    passed = failed = skipped = 0
    import re
    match = re.search(r"(\d+) passed", stdout); passed = int(match.group(1)) if match else 0
    match = re.search(r"(\d+) failed", stdout); failed = int(match.group(1)) if match else 0
    match = re.search(r"(\d+) skipped", stdout); skipped = int(match.group(1)) if match else 0
    result = "TIMEOUT" if timed_out else "PASS" if exit_code == 0 else "FAIL"
    classification = "PASS" if result == "PASS" else "TIMEOUT" if result == "TIMEOUT" else "ENVIRONMENT_FAILURE" if "No such file" in stderr or "ERR_MODULE" in stderr else "PREEXISTING_FAILURE_OR_TEST_FAILURE"
    return {"phase": phase, "command": " ".join(cmd), "working_directory": str(ROOT), "started_at": start, "completed_at": now(), "duration_seconds": round(time.monotonic() - started, 3), "exit_code": exit_code, "tests_passed": passed, "tests_failed": failed, "tests_skipped": skipped, "timeout": timed_out, "stdout_tail": stdout[-2000:], "stderr_tail": stderr[-2000:], "classification": classification, "evidence_path": str(out_path.relative_to(ROOT)), "stderr_path": str(err_path.relative_to(ROOT))}

def main() -> None:
    receipts = []
    for phase in GROUPS:
        receipt = run_phase(phase)
        receipts.append(receipt)
        OUT.write_text(json.dumps({"schema_version": "nexus.wp8.14e.regression.v1", "created_at": now(), "timeout_seconds": 90, "receipts": receipts, "all_pass": all(r["classification"] == "PASS" for r in receipts)}, indent=2) + "\n")
    print(json.dumps({"output": str(OUT.relative_to(ROOT)), "receipts": len(receipts), "all_pass": all(r["classification"] == "PASS" for r in receipts), "results": {r["phase"]: r["classification"] for r in receipts}}, indent=2))

if __name__ == "__main__": main()
