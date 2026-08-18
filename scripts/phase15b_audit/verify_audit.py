"""Verify Phase 15B audit artifact integrity without installing or probing tools."""

from __future__ import annotations

import json
import platform
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def _hardware_snapshot():
    snapshot = {"machine": platform.machine(), "platform": platform.platform(), "processor": platform.processor() or "UNKNOWN"}
    try:
        snapshot["memsize_bytes"] = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True, timeout=2).strip())
    except Exception:
        snapshot["memsize_bytes"] = "UNKNOWN"
    return snapshot


def verify() -> dict:
    audit_path = HERE / "phase15b_audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    candidates = audit.get("candidates", [])
    allowed_placements = {"RUN_ON_CURRENT_MAC", "RUN_ON_CURRENT_MAC_BOUNDED", "RUN_ON_REMOTE_OWNED_MACHINE", "DO_NOT_RUN"}
    placement_errors = [c["candidate_id"] for c in candidates if c.get("recommended_placement") not in allowed_placements]
    score_errors = [c["candidate_id"] for c in candidates if len(c.get("scores", {})) != 27]

    # The artifact contains rubric scores, not primary evidence of a free
    # hosted server.  Keep those claims explicitly unverified until a provider
    # contract, price/credit terms, and approved account evidence exist.
    free_server_claims = [
        {"candidate_id": c["candidate_id"], "candidate": c["candidate"], "score": c.get("scores", {}).get("free_server_availability"), "classification": "UNVERIFIED"}
        for c in candidates if c.get("scores", {}).get("free_server_availability", 0) >= 6
    ]
    return {
        "status": "PASS" if not placement_errors and not score_errors else "FAIL",
        "artifact": str(audit_path.relative_to(ROOT)),
        "candidate_count": len(candidates),
        "expected_candidate_count": audit.get("meta", {}).get("candidate_count"),
        "placement_integrity": "PASS" if not placement_errors else "FAIL",
        "placement_errors": placement_errors,
        "score_integrity": "PASS" if not score_errors else "FAIL",
        "score_errors": score_errors,
        "hardware_profile_claim": audit.get("meta", {}).get("host_profile", "UNKNOWN"),
        "hardware_runtime_snapshot": _hardware_snapshot(),
        "hardware_placement_verification": "PARTIAL — declared host profile is not independently proven by the artifact",
        "free_server_claims": free_server_claims,
        "free_server_verification": "UNVERIFIED — no provider contract or approved billing/credit evidence in Phase 15B artifact",
        "installation_performed": False,
        "provider_mutation_performed": False,
    }


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
