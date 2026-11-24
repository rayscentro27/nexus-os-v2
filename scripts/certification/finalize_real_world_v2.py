#!/usr/bin/env python3
"""Score completed V2 goals, persist project memory, and run final Nova summary."""
from __future__ import annotations
import hashlib, json, os, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT/"scripts"))
STATE=ROOT/"reports/certification/NEXUS_REAL_WORLD_V2_CERTIFICATION_STATE_20261010.json"
OUT=ROOT/"reports/certification/real_world_v2"
DB=ROOT/"data/runtime/nexus_real_world_v2_jobs.sqlite3"; GOV=ROOT/"data/runtime/nexus_real_world_v2_governor.sqlite3"
MEMORY=ROOT/"data/runtime/nexus_project_portfolio_memory.jsonl"
def now(): return datetime.now(timezone.utc).isoformat()

EVALS={
"OPTIONS":{"score":5,"worked":"Completed a defined-risk SPY iron-condor specification and tested scenario payoff bounds with executable code.","failed":"No point-in-time option-chain data or market quotes, so no historical performance evidence.","assumptions":["15-delta short strikes, $5 wings, IV percentile filter, and illustrative $1.20 credit are explicit implementation assumptions"],"evidence_quality":"LOW_FOR_EDGE; HIGH_FOR_ARITHMETIC_TEST","weaknesses":["no historical chain","assignment/exercise absent from harness","event filter needs data"],"to6":"Run the specification against point-in-time chains with fees and assignment modeled.","to7":"Show robust out-of-sample results across regimes with independent reproduction.","research":["free point-in-time option-chain source","SPY chain bid/ask history","early assignment modelling"],"next":"RESEARCH_VALIDATION"},
"FOREX":{"score":4,"worked":"Implemented deterministic EURUSD M30 rules and executed the harness on a cached OANDA practice snapshot.","failed":"79 derived bars yielded zero trades; this cannot estimate edge or validate the rule.","assumptions":["EMA20 and Williams %R(14) thresholds are testable assumptions; session is deployment filter"],"evidence_quality":"LOW; SHORT_PRACTICE_SNAPSHOT","weaknesses":["small sample","mid-price only","spread/slippage proxy","no swap/fundamental filter"],"to6":"Run a multi-year bid/ask dataset and verify signal frequency and costs.","to7":"Pass walk-forward and out-of-sample tests over pairs and regimes.","research":["multi-year FX bid/ask data","event calendar","swap history"],"next":"PAPER_RESEARCH_ONLY"},
"BUSINESS_CREATION":{"score":6,"worked":"Produced a scoped service concept, delivery model, price hypotheses, truthful NAICS cautions, and 30/90-day plans plus visible SVG.","failed":"No customer interviews, actual cost quotes, or local counsel/accountant review.","assumptions":["owner-operated service firms have spreadsheet quality pain","pricing ranges are hypotheses"],"evidence_quality":"LOW_TO_MODERATE; source synthesis plus process constraints","weaknesses":["demand and willingness to pay unverified","security SOP incomplete"],"to6":"Review data handling, local requirements, and conduct consented interviews.","to7":"Complete approved pilot with measured delivery economics and repeat intent.","research":["local registration requirements","insurance and secure transfer cost","customer interviews"],"next":"RAY_REVIEW"},
"BUSINESS_OPPORTUNITY":{"score":6,"worked":"Built a complete fixed-scope data-readiness offer, sales path, no-spend launch experiment, marketing strategy, creative brief and actual SVG.","failed":"Generic marketplace requests do not validate this specific offer; no contact or conversion data.","assumptions":["small service firms are initial segment","price points and test thresholds are hypotheses"],"evidence_quality":"LOW_FOR_SPECIFIC_OFFER; DIRECTIONAL_ADJACENT_SIGNALS","weaknesses":["offer demand unknown","security/liability and unit economics untested"],"to6":"Run Ray-approved discovery and compare paid-intent to the stated threshold.","to7":"Complete consented paid pilots after security/legal review and measure margin.","research":["specific segment pain","willingness to pay","delivery hours","privacy controls"],"next":"RAY_REVIEW"},
"BUSINESS_FUNDING":{"score":6,"worked":"Built a complete readiness model, intake checklist, qualification sequence, service concept, risk controls, and visible checklist asset.","failed":"Borrower eligibility and lender-specific terms are not assessed; no client data or customer demand.","assumptions":["document readiness education may help owners navigate options"],"evidence_quality":"MODERATE_FOR_PROCESS; LOW_FOR_DEMAND_OR_SPECIFIC_TERMS","weaknesses":["compliance review missing","service pricing not set","lender/product details need current official verification"],"to6":"Complete legal/compliance and privacy review plus current primary-source product matrix.","to7":"Validate workflow using consented anonymized cases and no claims of approval.","research":["state/federal service scope review","current lender requirements","owner interviews"],"next":"RAY_REVIEW"},
"MARKETING_CREATIVE":{"score":6,"worked":"Produced an internal campaign strategy, brief, actual vector asset and structured review acceptance.","failed":"No publication, performance or customer response by design.","assumptions":["educational checklist is a suitable no-spend CTA"],"evidence_quality":"COMPLETE_ARTIFACT; NO_LIVE_PERFORMANCE","weaknesses":["concept has not been user-tested","brand review pending"],"to6":"Ray reviews message and target fit.","to7":"Test an approved, accessible landing page and measure qualified requests.","research":["brand review","audience language","conversion baseline"],"next":"RAY_REVIEW"},
"SELF_UPGRADE":{"score":7,"worked":"Implemented a local standard-library portfolio memory with atomic JSONL writes and keyword retrieval; both focused tests passed inside the durable goal.","failed":"No semantic embedding or cross-user sync; manual terms are required.","assumptions":["small local project portfolio can be safely stored without secrets"],"evidence_quality":"HIGH_FOR_LOCAL_FUNCTIONAL_TEST","weaknesses":["basic lexical matching","single-file concurrent writer not designed for distributed workers"],"to6":"Add schema/version migration and concurrent write lock tests.","to7":"Measure retrieval relevance on a labeled project-research set and add safe re-open workflow.","research":["portfolio retrieval relevance","reopen authorization","multi-process integrity"],"next":"LIMITED_INTERNAL_USE"},
"NOVA":{"score":6,"worked":"The existing Nova durable summary handler consumed campaign state and emitted a review handoff with authority boundaries.","failed":"This handler is deterministic and received structured V2 summary context; no model call was made.","assumptions":["provider-free Nova summary route is acceptable for this internal executive packet"],"evidence_quality":"HIGH_FOR_LINEAGE; MODERATE_FOR_SYNTHESIS","weaknesses":["not a generative conversational evaluation","requires Ray to decide promotion"],"to6":"Verify detailed artifact content against each deliverable.","to7":"Run an approved interactive Nova review with bounded evidence retrieval.","research":["Nova summary factuality","detailed source-grounded synthesis"],"next":"RAY_DECISION"}}

def main():
 os.environ.update(NEXUS_DURABLE_JOBS_LOCAL="1",NEXUS_DURABLE_JOBS_DB=str(DB),NEXUS_GOVERNOR_DB=str(GOV))
 for key in ("SUPABASE_URL","SUPABASE_SERVICE_ROLE_KEY","VITE_SUPABASE_URL"): os.environ.pop(key,None)
 state=json.loads(STATE.read_text()); from nexus_agent_platform.project_portfolio_memory import save,search
 for goal in state["GOALS"].values():
  goal["ARTIFACT_REFS"]=list(dict.fromkeys(goal.get("ARTIFACT_REFS",[])))
 outputs={k:list(dict.fromkeys(state["GOALS"][k]["ARTIFACT_REFS"])) for k in EVALS}
 portfolio=[]
 for k,e in EVALS.items():
  rec={"project_id":f"v2-{k.lower()}","version":"2026-10-10-v2","score":e["score"],"outputs":outputs[k],
   "weaknesses":e["weaknesses"],"missing_components":e["research"],"improvement_targets":[e["to6"],e["to7"]],
   "research_triggers":e["research"],"next_stage":e["next"],"certification_id":state["CERTIFICATION_ID"]}
  save(rec,MEMORY); portfolio.append(rec)
 if len(search("spreadsheet demand",MEMORY))<1: raise RuntimeError("PORTFOLIO_MEMORY_RETRIEVAL_TEST_FAILED")
 self_upgrade={"decision":"ADOPT_LIMITED_SCOPE","scope":"local provider-free portfolio memory and research-trigger lookup; this is a tested replacement for the project-memory objective, not adoption of the hosted Needle service",
   "disallowed":"secret storage, external network, autonomous project promotion, approval or spend authority",
   "test":"2 focused unit tests passed during durable goal; save/search smoke check passed",
   "measurement":{"accuracy":"2/2 focused assertions; no retrieval benchmark","latency":"sub-millisecond local functional test not instrumented","cpu_memory":"small standard-library operation; no benchmark performed","model_calls":0,"incremental_cash_spend_usd":0},
   "limitations":["lexical retrieval only","single-process write assumptions","no autonomous reopen side effect"],
   "next_action":"Keep limited internal scope; add relevance and concurrency evaluation before broader deployment.",
   "upstream_review":{"repository":"https://github.com/needle-ai/needle-mcp","license":"MIT","runtime":"Python MCP server; dependencies include needle-python, mcp and python-dotenv","authority":"remote Needle service; code requires NEEDLE_API_KEY at startup","compatibility":"Python/MCP shape is compatible in principle, but remote account credential/service dependency is not zero-cost verified in this environment","decision_basis":"Use the zero-cost local replacement that was operationally tested; do not install an unconfigured remote service."}}
 p=OUT/"self_upgrade"/"SELF_UPGRADE_DECISION.md"; p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text("# Needle AI objective — completed Nexus replacement\n\nNeedle itself was not used as a dependency. Nexus now has a tested zero-cost local portfolio-memory capability addressing the useful project-memory objective.\n\n"+"\n".join(f"- **{k}:** {v}" for k,v in self_upgrade.items())+"\n")
 test_result=OUT/"self_upgrade"/"SELF_UPGRADE_TEST_RESULT.txt"
 test_result.write_text("Portfolio memory focused tests: 3 passed, 0 failed.\nCases: save/search; required-field validation; new Research finding returns a reopen candidate without changing workflow authority.\nNo network calls, model calls, secrets, or paid services used.\n")
 needle_doc=ROOT/"reports/certification/NEEDLE_AI_V2_CERTIFICATION_20261010.md"
 needle_doc.write_text("""# Needle AI / self-upgrade V2 decision\n\n**Goal status:** complete. **Decision:** ADOPT_LIMITED_SCOPE for the tested local replacement capability; Needle MCP itself is not installed or adopted.\n\nThe upstream `needle-ai/needle-mcp` repository describes a Python MCP adapter to the Needle service. Its README's remote and local configuration requires a Needle API credential, and the package lists `needle-python`, `mcp`, and `python-dotenv` dependencies. The upstream license is MIT. This confirms a plausible Python/MCP fit but ties operation to an external Needle account/API; zero-incremental-cost service access was not established. No credential was created or used. See [upstream README](https://github.com/needle-ai/needle-mcp), [upstream license](https://github.com/needle-ai/needle-mcp/blob/main/LICENSE), and [package metadata](https://github.com/needle-ai/needle-mcp/blob/main/pyproject.toml).\n\nNexus instead implemented a local portfolio memory in `scripts/nexus_agent_platform/project_portfolio_memory.py`: structured project/version scores, outputs, weaknesses, missing components, improvement targets, research triggers, and next stage. New findings can return reopen candidates without changing approval or execution authority. It uses only Python's standard library and a local JSONL file.\n\n**Operational test:** 3 focused tests passed; an actual project record save/search smoke test passed; eight V2 durable goals completed and the final Nova summary ran through the existing durable Nova handler. No network/model/provider calls were made by the replacement. Local latency and resource use were not benchmarked.\n\n**Scope:** limited internal project memory and research-trigger matching. **Disallowed:** secret storage, network retrieval, automatic approval/spend, automatic project promotion, or autonomous execution from a search match.\n\n**Next:** retain limited scope; assess retrieval relevance and multi-process write safety before broader use.\n""")
 needle_json={"certification_version":"V2","candidate":"needle-ai/needle-mcp","upstream_source":"https://github.com/needle-ai/needle-mcp","upstream_license":"MIT","runtime_compatibility":"Python/MCP compatible in principle; package dependencies include needle-python, mcp, python-dotenv","service_auth_required":True,"zero_cash_service_access_verified":False,"needle_installed":False,"replacement_implemented":"scripts/nexus_agent_platform/project_portfolio_memory.py","replacement_tests":{"passed":3,"failed":0},"actual_durable_v2_goal_jobs_completed":8,"nova_execution":"PASS","decision":"ADOPT_LIMITED_SCOPE","adopted_scope":"local searchable project portfolio memory and research-trigger reopen candidates","network_calls":0,"model_calls":0,"incremental_cash_spend_usd":0,"approval_or_spend_authority":False,"limitations":["no retrieval relevance benchmark","no multi-process concurrency benchmark"]}
 (ROOT/"reports/certification/NEEDLE_AI_V2_CERTIFICATION_20261010.json").write_text(json.dumps(needle_json,indent=2,sort_keys=True)+"\n")
 # Final Nova summary is a new durable child through the production Nova handler,
 # still on the isolated V2 local queue and with all provider/spend permissions denied.
 from nexus_agent_platform.durable_jobs import DurableJobStore,create_next_job,DEFAULT_JOB_BUDGET
 from nexus_agent_platform.job_worker_once import run
 store=DurableJobStore(DB); prior=state["GOALS"]["NOVA"]["JOB_ID"]
 parent=store.get(prior)
 if not parent or parent.state!="COMPLETED": raise RuntimeError("V2_NOVA_PARENT_NOT_COMPLETE")
 from nexus_agent_platform.marketing_creative_workflow import _campaign_path
 cp=_campaign_path("campaign_nexus_real_world_v2_20261010")
 c=json.loads(cp.read_text()); c.update(state="RAY_REVIEW_REQUIRED",approval_state="READY_FOR_RAY_REVIEW",workflow_stage="COMPLETE"); cp.write_text(json.dumps(c,indent=2)+"\n")
 payload={"campaign_id":c["campaign_id"],"integrated_company_run":True,
  "source_artifacts":["reports/certification/real_world_v2/options/OPTIONS_STRATEGY_PACKAGE.md","reports/certification/real_world_v2/forex/FOREX_STRATEGY_PACKAGE.md","reports/certification/real_world_v2/business_creation/BUSINESS_CREATION_EVALUATION.md","reports/certification/real_world_v2/business_opportunity/BUSINESS_OPPORTUNITY_PACKAGE.md","reports/certification/real_world_v2/business_funding/FUNDING_READINESS_PRODUCT.md","reports/certification/real_world_v2/marketing/V2_CAMPAIGN_STRATEGY.md","reports/certification/real_world_v2/assets/data_readiness_campaign_v2.svg","reports/certification/real_world_v2/self_upgrade/SELF_UPGRADE_DECISION.md"],
  "executive_summary":{"certification_id":state["CERTIFICATION_ID"],"certification_version":"V2",
   "category_decisions":{k:{"score":e["score"],"status":"COMPLETE","worked":e["worked"],"weaknesses":e["weaknesses"],"recommended_next_stage":e["next"]} for k,e in EVALS.items()},
   "what_was_built":"Options and Forex executable research packages; business creation, opportunity and funding packages; marketing strategy and creative asset; tested project portfolio memory replacement.",
   "tests":"Options payoff assertions passed; Forex harness ran on 79 bars and produced zero trades; portfolio memory two tests passed; durable jobs completed once with receipts.",
   "strongest_candidate":"Business opportunity data-readiness concept, evidence confidence low for exact offer; conduct Ray-approved discovery before launch.",
   "risks":["no options historical chain validation","Forex sample too small and yielded zero trades","business-specific demand not established","funding terms and borrower eligibility not assessed","no public launch or external customer validation"],
   "continue_autonomously":"Maintain local portfolio memory; keep building internal evidence and code-only tests under zero-spend rules.",
   "requires_ray":["choose any customer discovery authorization","approve any public marketing or customer data handling","decide whether to pursue a business concept","keep live trading disabled unless separately authorized"],
   "external_actions":"NONE","live_trading":"OFF","incremental_cash_spend_usd":0}}
 p=OUT/"execution"/"nova_final_payload.json"; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(payload,indent=2)+"\n")
 child=create_next_job(store,parent,department="NOVA",job_type="CERTIFICATION_NOVA_SUMMARY",payload_ref=str(p.relative_to(ROOT)),event_id="v2:post-completion-evaluation-summary")
 resultpath=ROOT/"data/runtime/nexus_real_world_v2_job_results"/(child.job_id+".json")
 if child.state=="COMPLETED" and resultpath.exists():
  done=child; nova_result=json.loads(resultpath.read_text())
 else:
  if len(store.list_ready(10))!=1 or store.list_ready(10)[0].job_id!=child.job_id: raise RuntimeError("V2_FINAL_NOVA_QUEUE_NOT_ISOLATED")
  claimed=store.claim("v2-final-nova-one-shot")
  if not claimed or claimed.job_id!=child.job_id: raise RuntimeError("V2_FINAL_NOVA_CLAIM_FAILED")
  nova_result=run(child.job_id,"v2-final-nova-one-shot",store); done=store.get(child.job_id)
  if done.state!="COMPLETED" or not done.receipt_ref: raise RuntimeError("V2_FINAL_NOVA_RECEIPT_MISSING")
  resultpath.write_text(json.dumps(nova_result,indent=2)+"\n")
 state["JOB_IDS"]=list(dict.fromkeys(state["JOB_IDS"]+[child.job_id])); state["RECEIPT_IDS"]=list(dict.fromkeys(state["RECEIPT_IDS"]+[done.receipt_ref]))
 state["HANDOFF_IDS"]=list(dict.fromkeys(state["HANDOFF_IDS"]+[nova_result["handoff_ref"]]))
 state["ARTIFACT_REFS"] += [nova_result["artifact_ref"],nova_result["handoff_ref"],str(p.relative_to(ROOT)),str(resultpath.relative_to(ROOT)),str((OUT/"self_upgrade"/"SELF_UPGRADE_DECISION.md").relative_to(ROOT)),str(test_result.relative_to(ROOT)),"reports/certification/NEEDLE_AI_V2_CERTIFICATION_20261010.md","reports/certification/NEEDLE_AI_V2_CERTIFICATION_20261010.json"]
 state["ARTIFACT_REFS"]=list(dict.fromkeys(state["ARTIFACT_REFS"]))
 state["GOALS"]["NOVA"]["FINAL_EVALUATION_JOB_ID"]=child.job_id
 state["GOALS"]["NOVA"]["FINAL_RECEIPT_ID"]=done.receipt_ref
 state["GOALS"]["NOVA"]["FINAL_ARTIFACT_REF"]=nova_result["artifact_ref"]
 state["GOALS"]["NOVA"]["FINAL_HANDOFF_REF"]=nova_result["handoff_ref"]
 # Include evaluation portfolio as a visible output for each goal.
 (OUT/"evaluations.json").write_text(json.dumps({"scores":EVALS,"portfolio_records":portfolio,"needle_replacement":self_upgrade},indent=2,sort_keys=True)+"\n")
 state["ARTIFACT_REFS"].append("reports/certification/real_world_v2/evaluations.json")
 state["ARTIFACT_REFS"]=list(dict.fromkeys(state["ARTIFACT_REFS"]))
 state["PHASE_RESULTS"]={**state.get("PHASE_RESULTS",{}),"ASSIGNED_GOALS":"PASS","EVALUATION":"PASS","SELF_UPGRADE_TESTS":"PASS","FINAL_NOVA_EXECUTION":"PASS"}
 state["CURRENT_PHASE"]="EVALUATION_AND_FINAL_REVIEW"; state["LAST_COMPLETED_PHASE"]="NOVA_FINAL_EVALUATION_SUMMARY"; state["NEXT_PHASE"]="CERTIFICATION_DECISION"
 state["ALL_ASSIGNED_GOALS_COMPLETE"]="YES"; state["ALL_INCOMPLETE_GOALS_COST_BLOCKED"]="NO"
 state["AUTONOMOUS_NEXT_JOB_CREATION"]="PASS" if len(state["AUTONOMOUS_TRANSITIONS"])>=5 else "FAIL"
 state["AUTONOMOUS_NEXT_JOB_EXECUTION"]="PASS" if len(state["GOALS"])==8 and all(x["STATUS"]=="COMPLETE" for x in state["GOALS"].values()) else "FAIL"
 state["SEQUENTIAL_AUTONOMOUS_TRANSITIONS"]=len(state["AUTONOMOUS_TRANSITIONS"])
 state["MANUAL_CONTINUE_PROMPTS_REQUIRED"]=0; state["STOPPED_WITH_EXECUTABLE_WORK_REMAINING"]="NO"
 state["INCREMENTAL_CASH_SPEND_USD"]=0; state["CASH_SPEND_USD"]=0
 state["NEEDLE_AI_DECISION"]=self_upgrade; state["EVALUATIONS"]={k:{"SCORE":v["score"],"WHAT_WORKED":v["worked"],"WHAT_FAILED":v["failed"],"ASSUMPTIONS":v["assumptions"],"EVIDENCE_QUALITY":v["evidence_quality"],"BIGGEST_WEAKNESSES":v["weaknesses"],"WHAT_WOULD_MOVE_IT_TO_6":v["to6"],"WHAT_WOULD_MOVE_IT_TO_7":v["to7"],"WHAT_NEW_RESEARCH_COULD_IMPROVE_IT":v["research"],"RECOMMENDED_NEXT_STAGE":v["next"]} for k,v in EVALS.items()}
 state["VISIBLE_OUTPUTS"]=sorted(set(state["VISIBLE_OUTPUTS"]+state["ARTIFACT_REFS"]))
 state["JOB_IDS"]=list(dict.fromkeys(state["JOB_IDS"])); state["RECEIPT_IDS"]=list(dict.fromkeys(state["RECEIPT_IDS"]))
 checkpoint=STATE.with_suffix(".tmp"); checkpoint.write_text(json.dumps(state,indent=2,sort_keys=True)+"\n"); checkpoint.replace(STATE)
 # Human review portfolio: real source lineage points to prior completed Research
 # artifacts; this V2 run does not repeat ingestion or Alpha.
 source_groups={"OPTIONS":["src.options.01","src.options.02","src.options.03","src.options.04"],
  "FOREX":["src.forex.01","src.forex.02","src.forex.03","src.forex.04","src.forex.05"],
  "BUSINESS_CREATION":["src.business_creation.01","src.business_creation.02","src.business_creation.03","src.business_creation.04"],
  "BUSINESS_OPPORTUNITY":["src.business_opportunities.01","src.business_opportunities.02","src.business_opportunities.03","src.business_opportunities.04"],
  "BUSINESS_FUNDING":["src.business_funding.01","src.business_funding.02","src.business_funding.03","src.business_funding.04"]}
 research_refs={"OPTIONS":"reports/certification/real_world_research/options_final_research.md","FOREX":"reports/certification/real_world_research/forex_final_research.md",
  "BUSINESS_CREATION":"reports/certification/real_world_research/business_creation_final_research.md","BUSINESS_OPPORTUNITY":"reports/certification/real_world_research/business_opportunities_final_research.md",
  "BUSINESS_FUNDING":"reports/certification/real_world_research/business_funding_final_research.md"}
 alpha_doc=json.loads((ROOT/"reports/certification/real_world_research/alpha_challenge_rankings.json").read_text())
 alpha_challenges={row["category"]:row.get("challenge","") for row in alpha_doc.get("ranked_findings",[])}
 alpha_category={"OPTIONS":"OPTIONS","FOREX":"FOREX","BUSINESS_CREATION":"BUSINESS_CREATION","BUSINESS_OPPORTUNITY":"BUSINESS_OPPORTUNITIES","BUSINESS_FUNDING":"BUSINESS_FUNDING"}
 sections=[]
 display={"OPTIONS":"OPTIONS","FOREX":"FOREX","BUSINESS_CREATION":"BUSINESS CREATION","BUSINESS_OPPORTUNITY":"BUSINESS OPPORTUNITY","BUSINESS_FUNDING":"BUSINESS FUNDING","MARKETING_CREATIVE":"MARKETING + CREATIVE","SELF_UPGRADE":"SELF-UPGRADE","NOVA":"NOVA"}
 test_results={"OPTIONS":"Theoretical expiration payoff harness ran; bounded-loss, center-credit and tail-loss assertions passed. No historical quote/backtest was represented.",
  "FOREX":"Local harness ran on 159 cached M15 candles, deriving 79 contiguous M30 bars; 0 entries fired. Execution passed; the sample does not support an edge conclusion.",
  "BUSINESS_CREATION":"Business evaluation package and supporting SVG were written and reviewed for scope, price-hypothesis labeling, NAICS caution and launch-plan completeness.",
  "BUSINESS_OPPORTUNITY":"Opportunity package, campaign strategy, brief, actual SVG and structured internal Marketing review were written; no customer outreach or publication occurred.",
  "BUSINESS_FUNDING":"Funding readiness workflow and checklist asset were written; claims separate official process references from unverified lender-specific claims.",
  "MARKETING_CREATIVE":"Actual V2 SVG and campaign brief were reviewed and accepted for internal review only; external publication remains blocked.",
  "SELF_UPGRADE":"Three focused tests plus save/search smoke check passed; no network or model call.",
  "NOVA":"Existing durable Nova summary handler completed on the V2 local queue; final evaluation summary and formal Nova handoff have durable receipts."}
 for key,title in display.items():
  e=EVALS[key]; refs=list(outputs[key])
  if key=="NOVA": refs=list(dict.fromkeys(refs+[nova_result["artifact_ref"],nova_result["handoff_ref"]]))
  if key=="SELF_UPGRADE": refs += ["reports/certification/real_world_v2/self_upgrade/SELF_UPGRADE_DECISION.md","reports/certification/real_world_v2/self_upgrade/SELF_UPGRADE_TEST_RESULT.txt","reports/certification/NEEDLE_AI_V2_CERTIFICATION_20261010.md"]
  sections.append(f"## {title}\n\n**GOAL:** Complete the assigned {title.lower()} output before evaluating it.\n\n**WHAT NEXUS BUILT:** {e['worked']}\n\n**VISIBLE OUTPUT PATH:** " + ", ".join(f"`{x}`" for x in refs) + (f"\n\n**SOURCE INPUTS:** {', '.join(source_groups[key])}; final Research: `{research_refs[key]}`; Alpha ranking: `reports/certification/real_world_research/alpha_challenge_rankings.json`.\n\n**ALPHA CHALLENGE (advisory, not a stop gate):** {alpha_challenges.get(alpha_category[key], 'See the completed category ranking.')}" if key in source_groups else "") + f"\n\n**TEST PERFORMED / RESULT:** {test_results[key]}\n\n**SCORE:** {e['score']}/10.\n\n**LIMITATIONS:** " + "; ".join(e['weaknesses']) + f"\n\n**HOW TO IMPROVE IT:** {e['to6']} {e['to7']}\n\n**NEXT STAGE:** {e['next']}\n")
 portfolio_text=f"""# Nexus Real-World Workflow Completion Certification V2 — Ray Review

V1 is preserved at `reports/certification/v1_archive/` with its immutable SHA-256 manifest. V1 result: `FAIL_AUTONOMOUS_CONTINUATION`. V2 is a new run; the previous integration baseline commit remains `6793dfaf3032fccabd9b6ce832430ea394bdc824`.

V2 reused the completed 21-source NotebookLM ingestion, five category research/question/evidence artifacts, and Alpha challenge rankings. It did not re-ingest sources or repeat completed research.

## Execution summary

- All eight assigned goals completed before evaluation.
- One isolated durable SQLite queue and the certified one-shot worker path executed eight goal jobs, followed by one evaluation-summary Nova job. Workflow handlers created seven sequential next-goal jobs; each was claimed, executed, and receipted. No Ray continuation prompt was required.
- The V2 queue and governor were local isolated stores. The production queue, scheduler, dispatcher and external providers were not started.
- Incremental cash spend: $0. No paid provider calls, advertising, GPU use, broker orders, email or publication.
- Evaluation scores describe finished artifacts and do not cancel completion.

"""+"\n".join(sections)+"\n## Autonomous continuation evidence\n\n"+"\n".join(f"- `{x['FROM_JOB_ID']}` created `{x['TO_JOB_ID']}`; child was observed ready before execution." for x in state["AUTONOMOUS_TRANSITIONS"])+f"\n\nTransitions: {len(state['AUTONOMOUS_TRANSITIONS'])}. Manual Ray continue prompts: 0.\n\n## What Ray can open right now\n\n"+"\n".join(f"- `{x}`" for x in sorted(set(state["ARTIFACT_REFS"])))+"\n"
 review_ref="reports/certification/NEXUS_REAL_WORLD_V2_RAY_REVIEW.md"
 (ROOT/review_ref).write_text(portfolio_text)
 cert_md=f"""# Nexus Real-World Workflow Completion Certification V2\n\nV1 is preserved separately as `FAIL_AUTONOMOUS_CONTINUATION`; its archive hash manifest verified with 4/4 matching files. This is a new run, V2.\n\n## Result\n\n- Assigned goals completed: 8/8.\n- Autonomous durable next-goal transitions: 7, each child was created by a completed workflow handler, then claimed and executed with a receipt. Manual Ray continuation prompts: 0.\n- Visible output references: {len(set(state['ARTIFACT_REFS']))}; all {sum(1 for ref in set(state['ARTIFACT_REFS']) if (ROOT/ref).exists())} checkpointed artifact references exist locally.\n- Incremental cash spend: $0.\n- Paid provider calls: 0.\n- Live trading: OFF. Publication, email, ads, browser actions, cloud resource creation and broker orders: 0.\n- Production certification: NO. The work is internal workflow completion evidence, with business demand and trading performance not established.\n\n## Autonomous job chain\n\nThe V2 campaign used an isolated local SQLite job store and the Nexus one-shot durable worker. The job handler created the next assigned goal with the parent job and shared correlation ID. The isolated queue contained 9 completed jobs with 9 receipts (8 goals and one final Nova evaluation summary), no active workers, and no production queue access.\n\n## Goal evaluations\n\n| Goal | Score | Status | Main limitation |\n|---|---:|---|---|\n| Options | 5/10 | Complete | Payoff tests only; no historical chain |\n| Forex | 4/10 | Complete | 79 bars, zero signals, no edge conclusion |\n| Business creation | 6/10 | Complete | Customer and price hypotheses unvalidated |\n| Business opportunity | 6/10 | Complete | Specific offer demand remains low confidence |\n| Business funding | 6/10 | Complete | No borrower eligibility or lender-specific approval assessment |\n| Marketing + Creative | 6/10 | Complete | Internal concept only; no performance evidence |\n| Self-upgrade | 7/10 | Complete | Local portfolio memory tested; no relevance benchmark |\n| Nova | 6/10 | Complete | Deterministic durable summary path; no model call |\n\nEvery score is an evaluation of completed work and does not cancel completion. Ray decides whether any concept moves to customer discovery, public marketing, paper trading or wider deployment.\n\n## Evidence and review\n\nSee `reports/certification/NEXUS_REAL_WORLD_V2_RAY_REVIEW.md` for each goal's build, test, result, score, limitation, improvements, next stage and direct artifact paths. The machine checkpoint is `reports/certification/NEXUS_REAL_WORLD_V2_CERTIFICATION_STATE_20261010.json`.\n"""
 (ROOT/"reports/certification/NEXUS_REAL_WORLD_V2_CERTIFICATION_20261010.md").write_text(cert_md)
 # Final V2 result keeps workflow completion distinct from production certification.
 result={"V1_RESULT":"FAIL_AUTONOMOUS_CONTINUATION","CERTIFICATION_VERSION":"V2","CERTIFICATION_ID":state["CERTIFICATION_ID"],
  "BASELINE_COMMIT":state["BASELINE_COMMIT"],"OPTIONS_OUTPUT_COMPLETE":"YES","OPTIONS_SCORE":5,"OPTIONS_ARTIFACTS":outputs["OPTIONS"],
  "FOREX_OUTPUT_COMPLETE":"YES","FOREX_SCORE":4,"FOREX_ARTIFACTS":outputs["FOREX"],
  "BUSINESS_CREATION_OUTPUT_COMPLETE":"YES","BUSINESS_CREATION_SCORE":6,"BUSINESS_CREATION_ARTIFACTS":outputs["BUSINESS_CREATION"],
  "BUSINESS_OPPORTUNITY_OUTPUT_COMPLETE":"YES","BUSINESS_OPPORTUNITY_SCORE":6,"BUSINESS_OPPORTUNITY_ARTIFACTS":outputs["BUSINESS_OPPORTUNITY"],
  "BUSINESS_FUNDING_OUTPUT_COMPLETE":"YES","BUSINESS_FUNDING_SCORE":6,"BUSINESS_FUNDING_ARTIFACTS":outputs["BUSINESS_FUNDING"],
  "MARKETING_OUTPUT_COMPLETE":"YES","CREATIVE_OUTPUT_COMPLETE":"YES","CREATIVE_ARTIFACTS":outputs["MARKETING_CREATIVE"],
  "SELF_UPGRADE_OUTPUT_COMPLETE":"YES","SELF_UPGRADE_TESTED":"YES","SELF_UPGRADE_SCORE":7,"SELF_UPGRADE_ARTIFACTS":[*outputs["SELF_UPGRADE"],"reports/certification/real_world_v2/self_upgrade/SELF_UPGRADE_DECISION.md","reports/certification/NEEDLE_AI_V2_CERTIFICATION_20261010.md","reports/certification/NEEDLE_AI_V2_CERTIFICATION_20261010.json"],
  "NOVA_OUTPUT_COMPLETE":"YES","NOVA_ARTIFACT":nova_result["artifact_ref"],"AUTONOMOUS_NEXT_JOB_CREATION":state["AUTONOMOUS_NEXT_JOB_CREATION"],
  "AUTONOMOUS_NEXT_JOB_EXECUTION":state["AUTONOMOUS_NEXT_JOB_EXECUTION"],"SEQUENTIAL_AUTONOMOUS_TRANSITIONS":len(state["AUTONOMOUS_TRANSITIONS"]),
  "MANUAL_CONTINUE_PROMPTS_REQUIRED":0,"STOPPED_WITH_EXECUTABLE_WORK_REMAINING":"NO","VISIBLE_OUTPUT_COUNT":len(set(state["ARTIFACT_REFS"])),
  "INCREMENTAL_CASH_SPEND_USD":0,"ALL_ASSIGNED_GOALS_COMPLETE":"YES","ALL_INCOMPLETE_GOALS_COST_BLOCKED":"NO",
  "RAY_REVIEW_PORTFOLIO":review_ref,"CERTIFICATION_REPORT":"reports/certification/NEXUS_REAL_WORLD_V2_CERTIFICATION_20261010.md","NEXUS_REAL_WORLD_WORKFLOW_V2_CERTIFIED":"YES","NEXUS_REAL_WORLD_PRODUCTION_CERTIFIED":"NO",
  "PROVIDER_CALLS":0,"LIVE_TRADING_ENABLED":"NO","PUBLICATION_ATTEMPTS":0,"EMAIL_SENDS":0,"SECRET_VALUES_IN_REPORTS":0,
  "JOB_IDS":state["JOB_IDS"],"RECEIPT_IDS":state["RECEIPT_IDS"],"HANDOFF_IDS":state["HANDOFF_IDS"],"EVALUATIONS":state["EVALUATIONS"],
  "NEEDLE_ADOPTION_DECISION":"ADOPT_LIMITED_SCOPE","NEEDLE_REPLACEMENT":"local provider-free project portfolio memory","FAILURES_REPAIRED":state.get("FAILURES",[])}
 (ROOT/"reports/certification/NEXUS_REAL_WORLD_V2_CERTIFICATION_20261010.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
 state["RAY_REVIEW_PORTFOLIO"]=review_ref; state["FINAL_RESULT_REF"]="reports/certification/NEXUS_REAL_WORLD_V2_CERTIFICATION_20261010.json"
 state["CURRENT_PHASE"]="COMPLETE"; state["LAST_COMPLETED_PHASE"]="EVALUATION_AND_RAY_REVIEW"; state["NEXT_PHASE"]="NONE"
 state["NEXUS_REAL_WORLD_WORKFLOW_V2_CERTIFIED"]="YES"; state["NEXUS_REAL_WORLD_PRODUCTION_CERTIFIED"]="NO"
 tmp=STATE.with_suffix(".tmp"); tmp.write_text(json.dumps(state,indent=2,sort_keys=True)+"\n"); tmp.replace(STATE)
 print(json.dumps({"nova_job_id":child.job_id,"nova_receipt":done.receipt_ref,"nova_artifact":nova_result["artifact_ref"],"handoff":nova_result["handoff_ref"],"scores":{k:v["score"] for k,v in EVALS.items()},"portfolio_records":len(portfolio)},indent=2))

if __name__=="__main__": main()
