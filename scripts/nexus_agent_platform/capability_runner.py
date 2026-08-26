"""Fixed adapter entry point for safe manifest capabilities.

The capability id is supplied by the broker from a manifest lookup, never by
model-generated command text. Adapters return structured evidence and do not
perform external or production actions.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))


def run(capability_id: str) -> dict:
    if capability_id == "system.health":
        from nexus_agent_platform.phase15.health_contract import build_health_status
        return {"status": "PASS", "evidence": build_health_status()}
    if capability_id == "proof.watchdog":
        from nexus_agent_platform.proof_watchdog import audit
        return {"status": "PASS", "evidence": audit([])}
    if capability_id == "research.alpha":
        from nexus_agent_platform.alpha_research import status_from_runtime
        return {"status": "PASS", "evidence": status_from_runtime()}
    if capability_id == "creative.intelligence":
        from nexus_agent_platform.creative.intelligence import creative_intelligence_portfolio
        return {"status": "PASS", "evidence": creative_intelligence_portfolio()}
    if capability_id == "forex.research":
        import subprocess
        result = subprocess.run(["python3", "scripts/trading/build_trading_hermes_brief.py", "--json"], cwd=ROOT, capture_output=True, text=True, timeout=120, check=False)
        return {"status": "PASS" if result.returncode == 0 else "FAIL", "evidence": result.stdout[-12000:], "stderr": result.stderr[-4000:]}
    if capability_id == "model.router":
        path = ROOT / "src/lib/hermesModelRoutingPolicy.ts"
        return {"status": "PASS" if path.exists() else "FAIL", "evidence": {"source": str(path), "exists": path.exists(), "mode": "read_only"}}
    raise KeyError(f"no fixed adapter for {capability_id}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: capability_runner.py <registered-capability-id>")
    print(json.dumps(run(sys.argv[1]), default=str))
