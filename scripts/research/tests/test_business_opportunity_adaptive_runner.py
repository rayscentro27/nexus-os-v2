from __future__ import annotations

import json
import sys
from contextlib import nullcontext
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"scripts/research"))

from research import notebook_playbook_runner as runner
from research import notebook_completion_contracts as contracts


class Adapter:
    def __init__(self): self.asked=[]
    def _job_slot(self): return nullcontext()
    def sources(self, notebook_id): return [{"id":"yt-source"}]
    def ask_notebook(self, notebook_id, prompt):
        self.asked.append((notebook_id,prompt))
        ids=[line.split("]",1)[0].strip("[") for line in prompt.splitlines() if line.startswith("[") and "]" in line]
        answer={"question_results":[{"question_id":qid,"evidence_status":"PARTIALLY_VERIFIED",
            "answer":"Evidence identified; price still needs independent source.","source_refs":["yt-source"]} for qid in ids]}
        return {"answer":json.dumps(answer),"references":[{"source_id":"yt-source"}],
            "submission_confirmed":True,"submission_attempted":True,"correlation_id":"turn-1"}


def test_alpha_director_question_is_executed_in_bound_notebook(monkeypatch,tmp_path):
    from nexus_agent_platform import business_opportunity_research_v2 as bo
    monkeypatch.setattr(bo,"CONTEXT_DIR",tmp_path)
    monkeypatch.setattr(bo,"CONTEXT_PATH",tmp_path/"opportunities.json")
    monkeypatch.setattr(runner.cases,"record_notebook_answer",lambda *a,**k:{"ok":True})
    monkeypatch.setattr(runner,"persist_completion_state",lambda *a,**k:"local:contract")
    monkeypatch.setattr(bo,"execute_research_director",lambda **kwargs:{"status":"PLANNED",
        "candidate_questions":[{"question":"Does a lower-cost affiliate offer exist for these buyers?",
            "materiality_topic":"monetization","why_material":"It changes launch cost.",
            "evidence_needed":"Current affiliate terms."}],"alternatives":[],"real_world_actions":[],
        "hypotheses_only":True,"model_execution":{"provider":"test","model":"fixture"}})
    adapter=Adapter()
    case={"case_id":"case-1","objective":"Research an online booking opportunity","opportunity_id":"opp-1"}
    state=contracts.new_contract_state(objective=case["objective"],research_purpose="MISSION_RESEARCH",
        research_domain="BUSINESS_OPPORTUNITY",notebook_id="dedicated-nb")
    result=runner._business_opportunity_director_review(state,case=case,event="AFTER_GROUP_A_DEFINITION",
        findings=[{"answer":"One source describes the offer but no pricing."}],adapter=adapter)
    assert result["ok"]
    assert result["hypotheses_only"]
    assert result["notebook_id"]=="dedicated-nb"
    assert len(adapter.asked)==1
    assert adapter.asked[0][0]=="dedicated-nb"
    adaptive=[row for row in state["required_questions"] if row.get("discovery_question")]
    assert len(adaptive)==1
    assert adaptive[0]["asked"] is True
    assert adaptive[0]["evidence_status"]=="PARTIALLY_VERIFIED"
    assert adaptive[0]["hypothesis_only_origin"]=="ALPHA_RESEARCH_DIRECTOR"


def test_youtube_source_intake_stays_in_feeder_until_alpha_promotes(monkeypatch,tmp_path):
    from contextlib import nullcontext
    from nexus_agent_platform import business_opportunity_research_v2 as bo
    from research import notebooklm_research_worker as worker
    monkeypatch.setattr(bo,"CONTEXT_DIR",tmp_path)
    monkeypatch.setattr(bo,"CONTEXT_PATH",tmp_path/"opportunities.json")
    monkeypatch.setattr(bo,"execute_research_director",lambda **kwargs:{"status":"PLANNED",
        "intake_classification":{"source_role":"BUSINESS_MODEL","relationship":"NEW_OPPORTUNITY",
            "promotion_decision":"PROMOTE_NEW"},"candidate_questions":[],"alternatives":[],
        "real_world_actions":[],"hypotheses_only":True})
    class FeederAdapter:
        def __init__(self): self.added_to=[]; self.asked=[]
        def video_id_of(self,url): return "video-1"
        def _job_slot(self): return nullcontext()
        def sources(self,notebook_id): return []
        def find_existing_source(self,*a,**k): return None
        def add_source(self,notebook_id,url,video_title):
            self.added_to.append(notebook_id); return {"id":"feeder-source-1"}
        def wait_for_source(self,notebook_id,source_id): return {"id":source_id,"status":"ready"}
        def ask_source_scoped(self,notebook_id,source_id,prompt):
            self.asked.append((notebook_id,source_id,prompt))
            return {"answer":"Claims a service for small restaurants.","references":[{"source_id":source_id}]}
    adapter=FeederAdapter()
    result=worker._business_opportunity_source_intake(work_item={"source_type":"YOUTUBE_VIDEO"},adapter=adapter,
        url="https://youtube.com/watch?v=video-1",title="AI services for independent restaurants",description="public video")
    assert result["ok"] and result["promoted"]
    assert adapter.added_to==["e0657f43-bf4e-4241-8336-7854739e942d"]
    assert adapter.asked[0][0]=="e0657f43-bf4e-4241-8336-7854739e942d"
    assert result["context"]["notebook_role"]=="PENDING_DEDICATED_RESEARCH"
    assert result["context"].get("notebook_id") is None

