"""Canonical Supabase Research findings, expert fan-out, and inbox contracts."""
from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from typing import Any
from nexus_agent_platform.research_work_queue import default_queue
from nexus_agent_platform.research_followup_contract import build_contract, question as contract_question
try:
    from social import _supabase as supabase
except Exception:
    supabase = None

EXPERTS = {
 "CLYDE_CREDIT":{"name":"Clyde","domain":"CREDIT"}, "GRANT_FUNDING":{"name":"Grant","domain":"FUNDING"},
 "ATLAS_OPPORTUNITY":{"name":"Atlas","domain":"BUSINESS_OPPORTUNITY"}, "MERCURY_TRADING":{"name":"Mercury","domain":"TRADING"},
 "FORGE_SYSTEMS":{"name":"Forge","domain":"SYSTEMS"}, "MIRA_MARKETING":{"name":"Mira","domain":"MARKETING"},
 "LEDGER_FINANCE":{"name":"Ledger","domain":"FINANCE"}, "SCOUT_INTELLIGENCE":{"name":"Scout","domain":"SEO_CUSTOMER_INTELLIGENCE"}}
ALL_EXPERTS=tuple(EXPERTS)
DOMAIN_TO_EXPERT={v["domain"]:k for k,v in EXPERTS.items()}
TERMS={"CREDIT":("credit","fico","utilization","derogatory","bureau","dispute"),"FUNDING":("funding","lender","sba","underwriting","business credit","grant"),"TRADING":("trading","forex","strategy","indicator","backtest","drawdown","repainting"),"SYSTEMS":("github","repo","repository","software","runtime","api","model","infrastructure","tool"),"MARKETING":("marketing","audience","campaign","funnel","conversion","lead","messaging"),"FINANCE":("cost","budget","afford","roi","spend","pricing"),"BUSINESS_OPPORTUNITY":("business opportunity","business model","monetiz","affiliate","consulting","customer problem"),"SEO_CUSTOMER_INTELLIGENCE":("seo","keyword","search demand","search intent","complaint","customer need","last-30-day")}
def _now(): return datetime.now(timezone.utc).isoformat()
def stable_id(prefix,value): return f"{prefix}_{hashlib.sha256(json.dumps(value,sort_keys=True,default=str).encode()).hexdigest()[:24]}"
def classify_finding(item,result):
 text=json.dumps({"item":item,"result":result},sort_keys=True,default=str).lower(); scores={d:sum(text.count(t) for t in ts) for d,ts in TERMS.items()}; ranked=sorted(((s,d) for d,s in scores.items() if s),reverse=True)
 if not ranked: return {"classification_status":"UNCLASSIFIED","classification_confidence":"LOW","primary_subject":"OTHER","secondary_subjects":[],"relevant_experts":list(ALL_EXPERTS)}
 top=ranked[0][0]; domains=[d for s,d in ranked if s>=max(1,top-1)]; return {"classification_status":"CLASSIFIED" if len(domains)==1 else "MULTI_DOMAIN_UNCERTAIN","classification_confidence":"HIGH" if top>=4 and len(domains)==1 else "MEDIUM" if top>=2 else "LOW","primary_subject":domains[0],"secondary_subjects":domains[1:],"relevant_experts":[DOMAIN_TO_EXPERT[d] for d in domains]}
def _write(table,row):
 if supabase is None or not supabase.configured(): return 0,"supabase_not_configured"
 return supabase.rest("POST",table,body=[row],prefer="return=representation,resolution=merge-duplicates")
def persist_finding_and_route(*,item,result,alpha=None):
 alpha=alpha or {}; c=classify_finding(item,result); fid=str(item.get("objective_id") or item.get("parent_finding_id") or result.get("research_id") or item.get("source_id") or stable_id("finding",item)); summary=result.get("what_was_learned") or result.get("new_information") or result.get("summary") or result.get("information_gain") or result.get("disposition") or "Research evidence persisted."
 finding={"finding_id":fid,"research_job_id":item.get("work_id"),"created_at":_now(),"updated_at":_now(),"source_type":item.get("source_type"),"source_name":item.get("title"),"source_url":item.get("source_url"),"source_date":item.get("published_at"),"source_author":item.get("source_author"),"source_channel":item.get("channel_name"),"raw_artifact_reference":result.get("artifact_root") or result.get("artifact_id"),"transcript_reference":result.get("transcript_path"),"content_hash":result.get("content_hash"),"research_mode":item.get("research_mode") or item.get("work_class"),"requested_by":item.get("requested_by"),"parent_finding_id":item.get("parent_finding_id"),"parent_department_request_id":item.get("parent_request_id"),"summary":summary,"claims":result.get("claims") or result.get("key_findings") or [],"evidence":result.get("evidence") or result.get("evidence_refs") or [],"unknowns":result.get("unknowns") or result.get("unresolved_questions") or result.get("remaining_gaps") or [],"contradictions":result.get("contradictions") or [],"followup_questions":result.get("next_action") or result.get("recommended_followup") or [],"primary_subject":c["primary_subject"],"secondary_subjects":c["secondary_subjects"],"tags":[item.get("source_type"),item.get("lane_id")],"entities":[item.get("source_id"),item.get("source_url")],"classification_status":c["classification_status"],"classification_confidence":c["classification_confidence"],"relevant_departments":c["relevant_experts"],"alpha_review_id":alpha.get("receipt_id") or alpha.get("evaluation_id"),"alpha_opinion":alpha.get("decision") or alpha.get("status") or "NOT_REVIEWED","scam_status":result.get("scam_status") or "UNKNOWN","status":"PERSISTED","finding":summary}
 finding.pop("status", None)
 status,response=_write("research_findings",finding)
 if status not in {200,201}: return {"status":"SUPABASE_WRITE_FAILED","finding_id":fid,"error":response,"classification":c}
 inboxes=[]
 for expert in c["relevant_experts"]:
  iid=stable_id("info",{"finding_id":fid,"expert_id":expert}); row={"information_item_id":iid,"finding_id":fid,"expert_id":expert,"why_relevant":f"Finding classified as {c['primary_subject']} for {EXPERTS[expert]['name']}.","priority":50,"created_at":_now(),"status":"PENDING","source_lineage":{"research_job_id":item.get("work_id"),"source_url":item.get("source_url")}}; s,r=_write("department_information_items",row); inboxes.append({"expert_id":expert,"information_item_id":iid,"status":"PENDING" if s in {200,201} else "WRITE_FAILED","error":r if s not in {200,201} else None})
 return {"status":"PERSISTED_AND_ROUTED","finding_id":fid,"classification":c,"inboxes":inboxes}
def create_expert_research_request(*,expert_id,assessment_id,parent_finding_id,question,required_evidence=None,preferred_source_types=None,parent_goal_id=None,parent_handoff_id=None,return_to_department=None,return_to_goal_id=None,decision_unlocked_by_answers=None,requesting_worker=None):
 rid=stable_id("expert_request",{expert_id,assessment_id,question})
 dept=return_to_department or EXPERTS.get(expert_id,{}).get("domain","RESEARCH")
 goal=return_to_goal_id or parent_goal_id or parent_finding_id
 required=list(required_evidence or ["source-backed answer"])
 sources=list(preferred_source_types or ["OFFICIAL_OR_PRIMARY"])
 questions=[contract_question(str(item),"SOURCE_BACKED_EVIDENCE",sources[min(i,len(sources)-1)],f"Attributable evidence directly answers: {item}") for i,item in enumerate(required)]
 if not questions: questions=[contract_question(question,"SOURCE_BACKED_EVIDENCE",sources[0],"Attributable evidence or explicit NOT_FOUND")]
 contract=build_contract(requesting_department=dept,reason=f"{expert_id} requires evidence to answer: {question}",research_questions=questions,overall_evidence_required=required,decision_unlocked_by_answers=decision_unlocked_by_answers or f"Resume the same {dept} goal with the evidence-backed answer.",return_to_department=dept,return_to_goal_id=goal,parent_goal_id=parent_goal_id or goal,parent_handoff_id=parent_handoff_id,requesting_worker=requesting_worker or expert_id,subject_type="RESEARCH_FINDING",subject_id=parent_finding_id,research_request_id=rid)
 row={"request_id":rid,"expert_id":expert_id,"assessment_id":assessment_id,"parent_finding_id":parent_finding_id,"research_question":question,"required_evidence":required,"preferred_source_types":sources,"created_at":_now(),"status":"OPEN","contract_payload":contract,"parent_goal_id":contract["parent_goal_id"],"parent_handoff_id":parent_handoff_id,"return_to_department":dept,"return_to_goal_id":goal,"requesting_worker":contract["requesting_worker"],"subject_type":contract["subject_type"],"subject_id":parent_finding_id,"decision_unlocked_by_answers":contract["decision_unlocked_by_answers"],"priority":contract["priority"],"updated_at":contract["updated_at"]}; s,r=_write("department_research_requests",row)
 if s not in {200,201}: return {"status":"SUPABASE_WRITE_FAILED","request_id":rid,"error":r}
 q=default_queue().enqueue(work_id=rid,work_class="ASSIGNED",source_type=(preferred_source_types or ["WEB_PAGE"])[0],source_id=rid,requested_by=expert_id,parent_request_id=rid,parent_finding_id=parent_finding_id,title=question,question=question,selection_reason="expert_request",research_mode="EXPERT_REQUEST"); return {"status":"QUEUED","request_id":rid,"queue_item":q}
def process_expert_information_item(*,information_item_id,disposition="LEARN_ONLY",reason="Finding reviewed against the expert domain.",next_research_question=None):
 if supabase is None or not supabase.configured(): return {"status":"SUPABASE_NOT_CONFIGURED"}
 s,rows=supabase.rest("GET",f"department_information_items?information_item_id=eq.{information_item_id}&limit=1")
 if s!=200 or not rows: return {"status":"INBOX_ITEM_NOT_FOUND","error":rows}
 inbox=rows[0]; expert=str(inbox.get("expert_id") or ""); fid=str(inbox.get("finding_id") or ""); fs,findings=supabase.rest("GET",f"research_findings?finding_id=eq.{fid}&limit=1"); ms,memory=supabase.rest("GET",f"department_knowledge?expert_id=eq.{expert}&limit=25")
 if fs!=200 or not findings: return {"status":"CANONICAL_FINDING_NOT_FOUND","finding_id":fid,"error":findings}
 aid=stable_id("assessment",{information_item_id,expert,fid}); assessment={"assessment_id":aid,"finding_id":fid,"expert_id":expert,"relevant_to_domain":"YES" if expert in (findings[0].get("relevant_departments") or []) else "MAYBE","what_is_new":findings[0].get("summary") or findings[0].get("finding"),"what_changed":"New canonical Research evidence is available.","confirms":"","contradicts":"","uncertainty":findings[0].get("unknowns") or [],"disposition":disposition,"reason":reason,"evidence":findings[0].get("evidence") or [],"next_action":"Await governed action authorization" if disposition in {"TEST","CREATE_INTERNAL_WORK"} else "Preserve domain learning","created_at":_now()}; ws,wr=_write("department_assessments",assessment)
 if ws not in {200,201}: return {"status":"ASSESSMENT_WRITE_FAILED","assessment_id":aid,"error":wr}
 ks,kr=_write("department_knowledge",{"knowledge_id":stable_id("knowledge",aid),"finding_id":fid,"expert_id":expert,"subject":findings[0].get("primary_subject"),"lesson":reason,"source_lineage":{"finding_id":fid},"assessment_lineage":{"assessment_id":aid},"result_lineage":{},"created_at":_now()})
 if ks not in {200,201}: return {"status":"KNOWLEDGE_WRITE_FAILED","assessment_id":aid,"error":kr}
 supabase.rest("PATCH",f"department_information_items?information_item_id=eq.{information_item_id}",body={"status":"EVALUATED","processed_at":_now(),"expert_assessment_id":aid},prefer="return=minimal"); followup=create_expert_research_request(expert_id=expert,assessment_id=aid,parent_finding_id=fid,question=next_research_question) if next_research_question else None
 return {"status":"EVALUATED","expert_id":expert,"finding_id":fid,"assessment_id":aid,"memory_records_loaded":len(memory or []) if ms==200 else 0,"followup":followup}
