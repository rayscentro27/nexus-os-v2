#!/usr/bin/env python3
"""Backfill current Alpha RESEARCH_MORE queue items into the canonical owner contract."""
from __future__ import annotations
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from nexus_agent_platform.governed import persistence
from nexus_agent_platform.research_followups import build_followup, persist_followup
from nexus_agent_platform.research_work_queue import default_queue

def rows(path):
    try: return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
    except: return []
def main():
    evaluations = rows(ROOT / "data/governed/alpha_evaluations.jsonl")
    receipts = {r.get("receipt_id"): r for r in [*rows(ROOT / "data/governed/alpha_evaluations.jsonl"), *[json.loads(p.read_text()) for p in (ROOT / "data/runtime/alpha_research").glob("alpha_receipt_*.json")]] if r.get("receipt_id")}
    queue = default_queue(); store = queue.load(); existing_requests = {r.get("request_id") or r.get("research_request_id") for r in rows(ROOT / "data/governed/research_requests.jsonl")}
    repaired=[]
    for item in store.get("items", []):
        if not item.get("alpha_followup_required") or item.get("status") not in {"QUEUED","WAITING","IN_PROGRESS"}: continue
        if item.get("owner") and item.get("fallback_sources") and (item.get("department") or item.get("department_target")): continue
        ev = next((r for r in evaluations if r.get("evaluation_id") == str(item.get("work_id","")).split(":")[-1] or r.get("request_id") == item.get("parent_request_id") or r.get("research_item_id") == item.get("objective_id")), {})
        receipt_id = ev.get("receipt_id") or item.get("parent_alpha_receipt_id") or f"orphan-{item.get('work_id')}"
        question = item.get("title") or item.get("question") or "Resolve the evidence deficiency identified by Alpha."
        source_refs = list(item.get("evidence_refs") or [])
        candidates = [{"source_type":"WEB_PAGE","source_id":f"source-ref-{i}","source_url":ref,"title":"Existing evidence reference"} for i,ref in enumerate(source_refs) if str(ref).startswith("http")]
        followup = build_followup(finding_id=str(item.get("objective_id") or item.get("source_id") or item.get("work_id")), alpha_receipt_id=str(receipt_id), alpha_request_id=str(item.get("parent_request_id") or ""), missing_evidence=[question], question=question, package={"query":question, "lane_id": item.get("lane_id"), "department": item.get("department_target"), "research_mode": item.get("research_mode"), "objective_id": item.get("objective_id")}, project_id=item.get("objective_id"), source_candidates=candidates, work_id=item.get("work_id"))
        if followup["research_request_id"] not in existing_requests:
            persist_followup(followup); existing_requests.add(followup["research_request_id"])
        else:
            # Still repair the operational projection when the immutable
            # request already exists.
            queue.upsert({**item, **followup, "status": item.get("status")})
        repaired.append({"work_id": item.get("work_id"), "owner": followup["owner"], "department": followup["department"], "research_request_id": followup["research_request_id"]})
    # Include projections written during this migration before de-duplicating.
    store = queue.load()
    # The first bounded repair may have emitted a projection with a new work
    # id before the legacy id was recognized. Preserve its audit record but
    # supersede it so one Alpha return has one executable queue item.
    canonical = {str(row.get("parent_alpha_receipt_id")): row for row in store.get("items", []) if row.get("alpha_followup_required") and str(row.get("work_id", "")).startswith("alpha-model-followup:") and row.get("parent_alpha_receipt_id")}
    for row in store.get("items", []):
        if not str(row.get("work_id", "")).startswith("research-followup:") or row.get("status") in {"SUPERSEDED", "COMPLETE"}: continue
        match = canonical.get(str(row.get("parent_alpha_receipt_id")))
        if match:
            row.update({"status":"SUPERSEDED", "last_result":{"classification":"DUPLICATE_PROJECTION_SUPERSEDED", "duplicate_of":match.get("work_id")}, "completed_at":__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()})
    queue._save(store)
    print(json.dumps({"repaired":repaired,"count":len(repaired),"duplicate_requests_created":0,"external_actions":0}, sort_keys=True))
if __name__ == "__main__": main()
