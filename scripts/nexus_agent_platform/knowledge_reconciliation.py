"""Deterministic Supabase knowledge-delivery reconciliation."""
from __future__ import annotations
from typing import Any
from nexus_agent_platform.supabase_knowledge import _write


def reconcile_finding(finding_id: str) -> dict[str, Any]:
    from nexus_agent_platform import supabase_knowledge as knowledge
    if knowledge.supabase is None or not knowledge.supabase.configured(): return {"status":"SUPABASE_NOT_CONFIGURED","finding_id":finding_id}
    status, findings = knowledge.supabase.rest("GET", f"research_findings?finding_id=eq.{finding_id}&limit=1")
    if status != 200 or not findings: return {"status":"FINDING_NOT_FOUND","finding_id":finding_id}
    expected=findings[0].get("relevant_departments") or []; status,inboxes=knowledge.supabase.rest("GET",f"department_information_items?finding_id=eq.{finding_id}"); existing={r.get("expert_id") for r in (inboxes or [])} if status==200 else set(); repaired=[]
    for expert in [e for e in expected if e not in existing]:
        iid=knowledge.stable_id("info",{"finding_id":finding_id,"expert_id":expert}); code,response=_write("department_information_items",{"information_item_id":iid,"finding_id":finding_id,"expert_id":expert,"why_relevant":"Reconciled missing delivery.","priority":50,"status":"PENDING","source_lineage":{"finding_id":finding_id}}); repaired.append({"expert_id":expert,"information_item_id":iid,"status":"REPAIRED" if code in {200,201} else "FAILED","error":response if code not in {200,201} else None})
    return {"status":"RECONCILED","finding_id":finding_id,"expected_experts":expected,"existing_experts":sorted(existing),"missing":[e for e in expected if e not in existing],"repaired":repaired}
