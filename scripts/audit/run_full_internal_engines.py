#!/usr/bin/env python3
"""Run every requested safe internal engine and record honest per-command proof."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from full_engine_common import write_report  # noqa: E402

COMMANDS = [
    ("npm_continuous_loop", ["npm", "run", "nexus:loop", "--", "--once"], ["reports/runtime/continuous_loop_status_latest.json"]),
    ("full_activation", [sys.executable, "scripts/activation/run_nexus_full_activation.py", "--run-all", "--json"], ["reports/runtime/nexus_full_activation_latest.json"]),
    ("continuous_loop", [sys.executable, "scripts/activation/run_nexus_continuous_loop.py", "--once", "--json", "--safe-internal", "--local-only", "--feedback-enabled"], ["reports/runtime/continuous_loop_status_latest.json"]),
    ("repo_concept_extraction", [sys.executable, "scripts/activation/run_repo_concept_extraction.py", "--json"], ["reports/runtime/repo_concept_extraction_latest.json"]),
    ("client_portal_backend", [sys.executable, "scripts/client_flow/run_client_portal_backend_build.py", "--json"], ["reports/runtime/client_portal_backend_build_latest.json"]),
    ("connector_harness", [sys.executable, "scripts/connectors/run_connector_test_harness.py", "--json"], ["reports/runtime/connector_test_harness_latest.json"]),
    ("dispute_simulation", [sys.executable, "scripts/disputes/run_dispute_simulation_lab.py", "--json"], ["reports/runtime/dispute_simulation_lab_latest.json"]),
    ("youtube_review_proof", [sys.executable, "scripts/activation/run_youtube_review_proof.py", "--json"], ["reports/runtime/youtube_review_proof_latest.json"]),
    ("social_connector_proof", [sys.executable, "scripts/social/run_social_connector_proof.py", "--json"], ["reports/runtime/social_connector_proof_latest.json"]),
]


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--json", action="store_true"); args = parser.parse_args()
    results = []
    for name, cmd, outputs in COMMANDS:
        found = cmd[0] == "npm" or (ROOT / cmd[1]).exists()
        item = {"engine": name, "found": found, "ran": False, "passed": False, "failed": False,
                "command": " ".join(cmd), "outputs_created": [], "dashboard_client_admin_visibility": "report-backed; see engine matrix",
                "external_action_attempted": False, "approval_cards_created": 0, "next_required_setup": "none"}
        if not found:
            item.update({"failed": True, "next_required_setup": "Restore missing command."}); results.append(item); continue
        try:
            proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=900)
            item["ran"] = True; item["passed"] = proc.returncode == 0; item["failed"] = proc.returncode != 0
            item["exit_code"] = proc.returncode; item["stderr_tail"] = proc.stderr[-500:]
            item["outputs_created"] = [path for path in outputs if (ROOT / path).exists()]
            if proc.returncode:
                item["next_required_setup"] = "Inspect stderr and the engine report; later engines continued."
        except Exception as exc:  # noqa: BLE001
            item.update({"ran": True, "failed": True, "error": str(exc), "next_required_setup": "Inspect local runtime error."})
        results.append(item)
    report = {"ok": all(item["passed"] for item in results), "mode": "safe_internal_local_only", "status": "internal_active",
        "external_action_performed": False, "engines_found": sum(item["found"] for item in results),
        "engines_run": sum(item["ran"] for item in results), "engines_passed": sum(item["passed"] for item in results),
        "engines_failed": sum(item["failed"] for item in results), "engines": results,
        "summary": f"Ran {sum(item['ran'] for item in results)} safe internal engine commands; {sum(item['passed'] for item in results)} passed."}
    write_report("full_internal_engine_run", "Full Internal Engine Run", report, {"Engine results": results})
    print(json.dumps(report, indent=2) if args.json else report["summary"])
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
