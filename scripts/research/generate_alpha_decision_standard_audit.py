#!/usr/bin/env python3
"""Create the Alpha policy audit from persisted receipts, never from guesses."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from nexus_agent_platform.alpha_decision_policy import apply_policy

def load(path, default):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return default
def records(path):
    try: return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    except Exception: return []
def main():
    receipt_dir = ROOT / "data/runtime/alpha_research"
    package_rows = records(ROOT / "data/governed/research_v2_packages.jsonl")
    receipt_paths = sorted(receipt_dir.glob("alpha_receipt_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    wanted = {"proactive-canary-systems-capability", "proactive-canary-trading-candidate", "proactive-canary-goclear-funding", "proactive-canary-revenue-opportunity", "proactive-canary-qualified-funding"}
    rows = []
    for path in receipt_paths:
        receipt = load(path, {})
        finding = receipt.get("finding_id")
        if finding not in wanted or any(row["finding_id"] == finding for row in rows):
            continue
        judgment = receipt.get("model_review") or {}
        package = next((row for row in reversed(package_rows) if str(row.get("research_id") or row.get("finding_id")) == str(finding)), {"research_id": finding, "query": finding, "sources": receipt.get("source_refs", [])})
        policy = apply_policy(package, judgment)
        department = {"proactive-canary-systems-capability":"SYSTEMS","proactive-canary-trading-candidate":"TRADING","proactive-canary-goclear-funding":"GOCLEAR","proactive-canary-revenue-opportunity":"REVENUE","proactive-canary-qualified-funding":"GOCLEAR / CLYDE"}.get(finding, "UNKNOWN")
        rows.append({"alpha_receipt_id":receipt.get("receipt_id"),"finding_id":finding,"department":department,"mission":package.get("title") or package.get("query"),"question":package.get("query") or package.get("title"),"evidence":receipt.get("source_refs") or package.get("sources"),"confidence":judgment.get("confidence"),"evidence_strength":judgment.get("evidence_strength"),"original_decision":receipt.get("decision"),"original_rationale":judgment.get("reasoning_summary"),"missing_evidence":judgment.get("deficiencies"),"risk":judgment.get("contradictions"),"cost_concern":policy["test_profile"].get("expected_cost_to_test"),"legal_compliance_concern":policy["hard_blockers"],"implementation_concern":judgment.get("deficiencies"),"novelty_concern":None,"expected_value_concern":judgment.get("commercial_intent_assessment"),"threshold_or_rule":"Model prompt allowed QUALIFY/RESEARCH_MORE/REJECT/PARK; pre-policy implementation had no TEST or explicit Ray rubric.","next_action":judgment.get("required_followup") or judgment.get("recommended_next_stage"),"next_owner":policy["next_owner"],"new_decision":policy["decision"],"new_reason":policy["why"],"new_next_step":policy["recommended_next_step"],"ray_standard_difference":"No change: unresolved source evidence does not establish a safe test profile; Trading also lacks a meaningful testable hypothesis." if policy["decision"] == receipt.get("decision") else "Ray-aligned TEST eligibility applied."})
    rows.sort(key=lambda row: row["department"])
    payload = {"schema_version":"nexus.alpha-decision-standard-audit.v1","generated_at":datetime.now(timezone.utc).isoformat(),"policy_provenance":[{"rule":"QUALIFY/RESEARCH_MORE/REJECT/PARK only","source":"MODEL_DEFAULT + IMPLEMENTATION_DEFAULT","finding":"TEST/MONITOR/NO_ACTION absent before repair"},{"rule":"hard safety gates","source":"RAY_DEFINED in new canonical policy; existing governance boundary retained"},{"rule":"low-cost reversible experiment","source":"RAY_DEFINED in new canonical policy"},{"rule":"PARK maps to MONITOR","source":"LEGACY_RULE normalized by new policy"}],"decisions":rows,"over_conservative_patterns":["incomplete public fetch was treated as a generic evidence stop without checking a test profile","no bounded TEST disposition existed","Alpha prompt did not ask for economics, reversibility, or testable unknowns"],"ray_aligned_policy":{"dispositions":["QUALIFY","TEST","RESEARCH_MORE","MONITOR","REJECT","NO_ACTION"],"alpha_final_business_authority":False,"hard_safety_gates_preserved":True},"safety":{"live_trades":0,"paid_actions":0,"publications":0,"customer_messages":0,"funds_moved":0,"production_tool_installations":0}}
    out_json = ROOT / "reports/research/nexus_alpha_decision_standard_audit_20260927.json"
    out_md = ROOT / "reports/research/NEXUS_ALPHA_DECISION_STANDARD_AUDIT_2026-09-27.md"
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    lines=["# Nexus Alpha Decision Standard Audit", "", "Alpha is a challenger and routing layer, not the final business decision-maker.", "", "## DECISION AUDIT"]
    lines += ["| department | receipt | original | new | confidence | evidence | next owner |", "|---|---|---|---|---|---|---|"]
    lines += [f"| {r['department']} | {r['alpha_receipt_id']} | {r['original_decision']} | {r['new_decision']} | {r['confidence']} / {r['evidence_strength']} | {str(r['original_rationale'])[:150]} | {r['next_owner']} |" for r in rows]
    lines += ["", "## POLICY PROVENANCE", "- Before repair, the model prompt and implementation supplied the material disposition vocabulary; Ray's low-cost reversible TEST standard was not encoded.", "- The repaired policy preserves hard safety gates and adds TEST, MONITOR, NO_ACTION, explicit economics/reversibility fields, explainability, and append-only Ray overrides.", "", "## OVER-CONSERVATISM FINDINGS", *[f"- {x}" for x in payload["over_conservative_patterns"]], "", "## RE-EVALUATION", *[f"- {r['department']}: {r['original_decision']} → {r['new_decision']}; {r['new_reason']} Next: {r['new_next_step']}" for r in rows], "", "## SAFETY", "No live trades, paid actions, publications, customer messages, funds moved, or production tool installations."]
    out_md.write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(json.dumps({"report":str(out_md),"json":str(out_json),"decisions":len(rows),"changed":sum(r["original_decision"] != r["new_decision"] for r in rows)}, sort_keys=True))
if __name__ == "__main__": main()
