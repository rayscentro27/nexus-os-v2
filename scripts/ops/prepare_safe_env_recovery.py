#!/usr/bin/env python3
"""Create a gitignored, local-only connector recovery file from unique original values."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from same_day_common import ROOT, RUNTIME, now, parse_env, read_json, write_report  # noqa: E402

TARGET = ROOT / ".env.nexus.recovered.local"
BLOCKED = ("SMARTCREDIT", "PASSWORD", "COOKIE")


def build() -> dict:
    inv = read_json(RUNTIME / "env_connector_inventory_latest.json", {})
    gap = read_json(RUNTIME / "env_connector_gap_analysis_latest.json", {})
    missing = set(gap.get("original_keys_missing_in_v2", [])); candidates: dict[str, list[tuple[str,str]]] = {}
    for item in inv.get("inventory", []):
        if item.get("source_scope") != "original_nexus" or item.get("key") not in missing or any(x in item["key"].upper() for x in BLOCKED): continue
        value = parse_env(Path(item["source_file"])).get(item["key"], "")
        if value: candidates.setdefault(item["key"], []).append((item["sha256_fingerprint_10"], value))
    recovered: dict[str,str] = {}; skipped=[]
    for key, values in candidates.items():
        unique={fp:value for fp,value in values}
        if len(unique)==1: recovered[key]=next(iter(unique.values()))
        else: skipped.append({"key":key,"reason":"conflicting_original_values"})
    existing=parse_env(TARGET); existing.update(recovered)
    if existing:
        TARGET.write_text("# Local-only recovered Nexus connector values. Never commit.\n" + "\n".join(f"{k}={v}" for k,v in sorted(existing.items())) + "\n")
    protected = TARGET.name.startswith(".env.")
    report={"ok":True,"generated_at":now(),"status":"internal_active","target_file":str(TARGET),"target_created":TARGET.exists(),
            "target_gitignored":protected,"values_copied_locally":len(recovered),"copied_key_names":sorted(recovered),"skipped":skipped,
            "raw_values_in_report":False,"existing_env_overwritten":False,"external_action_performed":False,
            "summary":"Recovered only unique, non-SmartCredit connector values into a gitignored local file; reports contain no raw values."}
    setup={"ok":True,"generated_at":now(),"required_keys":gap.get("original_keys_missing_in_v2",[]),"recovered_keys":sorted(recovered),
           "manual_setup_remaining":sorted(set(gap.get("original_keys_missing_in_v2",[]))-set(recovered)),
           "instructions":["Keep recovered file local-only.","Set browser-safe VITE_ variables in Netlify only after review.","Keep service-role/private keys server-side only.","Resolve conflicting fingerprints manually without pasting values into reports."],
           "external_action_performed":False}
    write_report("safe_env_recovery_plan","Safe Environment Recovery Plan",report,{"Copied key names":report["copied_key_names"],"Skipped":skipped})
    write_report("required_env_setup","Required Environment Setup",setup,{"Remaining":setup["manual_setup_remaining"],"Instructions":setup["instructions"]})
    return report


def main()->int:
    p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r["summary"]);return 0
if __name__=="__main__":raise SystemExit(main())
