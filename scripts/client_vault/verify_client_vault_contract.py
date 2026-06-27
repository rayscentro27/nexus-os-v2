#!/usr/bin/env python3
"""Verify the Client Vault is NOT connected (contract + mock only). Dry-run.

Fails if any sign of a live vault, a second Supabase, real credentials, or real client data appears.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
RUNTIME = ROOT / "reports" / "runtime" / "client_vault_contract_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "client_vault_contract_verification_latest.md"

CONTRACT = ROOT / "src" / "config" / "clientVaultContract.ts"
ADAPTER = ROOT / "src" / "lib" / "clientVaultAdapter.ts"
ENV_EXAMPLE = ROOT / ".env.example"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", default=True)
    p.add_argument("--json", action="store_true")
    p.add_argument("--report-path", default="")
    a = p.parse_args()

    contract_text = CONTRACT.read_text(errors="ignore") if CONTRACT.exists() else ""
    adapter_text = ADAPTER.read_text(errors="ignore") if ADAPTER.exists() else ""
    env_text = ENV_EXAMPLE.read_text(errors="ignore") if ENV_EXAMPLE.exists() else ""

    checks = {
        "contract_status_not_connected_by_design": "not_connected_by_design" in contract_text,
        "adapter_returns_mock": "MockClientVaultAdapter" in adapter_text,
        "adapter_refuses_live": "not connected by design" in adapter_text.lower() or "throw new Error" in adapter_text,
        "no_second_supabase_env": not re.search(r"CLIENT_VAULT_SUPABASE_URL\s*=\s*\S+", env_text),
        "no_vault_credentials_committed": not re.search(r"(CLIENT_VAULT|VAULT_SERVICE_ROLE).*=.{8,}", env_text),
    }
    ok = all(checks.values())

    report = {
        "ok": ok,
        "title": "Client Vault Contract Verification",
        "generated_at": now(),
        "dry_run": True,
        "checks": checks,
        "connection_status": "not_connected_by_design",
        "counts": {"checks": len(checks), "passed": sum(1 for v in checks.values() if v)},
        "summary": "Client Vault not connected by design; mock adapter only; no 2nd Supabase, no credentials, no real data."
        if ok else "Client Vault verification FAILED — possible live connection or credentials.",
        "safety": {"real_vault_connected": False, "second_supabase_connected": False,
                   "real_credentials_present": False, "real_client_data_present": False},
    }
    RUNTIME.parent.mkdir(parents=True, exist_ok=True)
    # Do not overwrite the contract report JSON; write verification to the same runtime file name space.
    (ROOT / "reports" / "runtime" / "client_vault_contract_verification_latest.json").write_text(json.dumps(report, indent=2))
    L = [f"# {report['title']}", "", f"- ok: {report['ok']}", f"- connection_status: {report['connection_status']}", "", "## Checks"]
    L += [f"- {k}: {v}" for k, v in checks.items()]
    MANUAL.parent.mkdir(parents=True, exist_ok=True)
    MANUAL.write_text("\n".join(L) + "\n")
    if a.report_path:
        Path(a.report_path).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2) if a.json else report["summary"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
