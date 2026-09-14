#!/usr/bin/env python3
"""Bounded six-lane public-source Research -> Alpha -> handoff cycle."""
from __future__ import annotations
import hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "scripts"))
from alpha.alpha_discovery import retrieve_page
from nexus_agent_platform.governed.persistence import append_record
from nexus_agent_platform.research_rotation import select_next_lane
RUN = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
ARTIFACT = ROOT / "reports/runtime" / f"research_solution_rotation_{RUN}.json"
REPORT = ROOT / "reports/runtime" / f"research_solution_rotation_{RUN}.md"
LANES = [
 ("AFFILIATE_REVENUE","GoClear affiliate and referral programs with current public terms","Marketing",[("HubSpot Affiliate Program","https://www.hubspot.com/partners/affiliates"),("Intuit Product Referrals","https://quickbooks.intuit.com/partners/referrals/")]),
 ("CREDIT_REPAIR","Credit-repair fulfillment models and compliance constraints","GoClear Operations",[("FTC Credit Repair Organizations Act","https://www.ftc.gov/legal-library/browse/statutes/credit-repair-organizations-act"),("CFPB credit repair guidance","https://www.consumerfinance.gov/ask-cfpb/what-is-the-difference-between-credit-counseling-and-debt-settlement-debt-consolidation-or-credit-repair-en-1449/")]),
 ("GRANTS_GOVERNMENT","Current grants and legitimate applicant-model fit for GoClear","Grants",[("SBA Grants","https://www.sba.gov/loans/additional-funding-opportunities/grants/"),("SBA Grow Your Business funding guidance","https://www.sba.gov/counseling/grow-your-business/")]),
 ("SEO_SEARCH_DEMAND","Current SEO demand signals and measurable GoClear content tests","Marketing",[("Google Search Central documentation","https://developers.google.com/search/docs"),("Google Search Console","https://search.google.com/search-console/about")]),
 ("MERCHANDISE_POD","POD pricing, fulfillment, and cheapest demand experiment","Creative",[("Printify T-shirt pricing","https://printify.com/t-shirt-pricing-calculator/"),("Printify cost model","https://help.printify.com/hc/en-us/articles/4483638151569-Does-Printify-cost-anything")]),
 ("REAL_ESTATE_AI","Arizona/Nevada AI-assisted brokerage model and advertising boundaries","Systems",[("Arizona real-estate law and advertising","https://azre.gov/sites/default/files/2025-07/Law%20Book.pdf"),("Nevada real-estate statute","https://www.leg.state.nv.us/nrs/NRS-645.html")]),
]
def main() -> int:
    outputs=[]
    for lane, question, owner, sources in LANES:
        rid=f"research_rotation_{RUN}_{lane.lower()}"; now=datetime.now(timezone.utc).isoformat()
        append_record("research_requests",{"request_id":rid,"lane":lane,"question":question,"status":"RESEARCHING","requested_by":"research_heartbeat","created_at":now,"solution_seeking":True})
        evidence=[]
        for title,url in sources:
            page=retrieve_page(url,timeout=25); text=page.get("text") or page.get("excerpt") or page.get("error") or ""
            evidence.append({"title":title,"url":url,"status":"SUCCESS" if page.get("ok") else "FAILED","retrieved_at":page.get("retrieved_at"),"excerpt":text[:1800],"source_quality":"PRIMARY" if any(x in url for x in ("ftc.gov","consumerfinance.gov","sba.gov","developers.google.com","azre.gov","leg.state.nv.us")) else "PROVIDER_OFFICIAL"})
        alpha={"alpha_review_id":f"alpha_solution_{RUN}_{lane.lower()}","research_id":rid,"classification":"EXPERIMENT" if any(x["status"]=="SUCCESS" for x in evidence) else "RESEARCH_MORE","strengths":["current public source evidence exists","bounded test path is possible"],"weaknesses":["business outcome is not yet observed"],"missing_evidence":["search volume","conversion","CAC","realized revenue","approval status"],"how_it_could_work":f"Use verified source facts to create a narrow {lane.lower()} test without assuming demand or approval.","alternative_model":"consulting or education first where truthful, otherwise referral/partner model","risk":"claims, eligibility, economics, and compliance require validation","legal_or_compliance_boundary":"no deceptive claims, no external submission, no spend or binding agreement","cheapest_test":f"Create one governed {lane.lower()} brief and measure qualified response before scaling.","success_metric":"source-backed engagement or qualified lead/action; value UNKNOWN before measurement","failure_learning":"identify which evidence or audience assumption failed","next_handoff":owner,"created_at":now}
        append_record("alpha_evaluations",{"evaluation_id":alpha["alpha_review_id"],"research_item_id":rid,"decision":"FOLLOW_UP_RESEARCH","status":"SOLUTION_SEEKING","score":50,"reasoning":"Evidence supports continued bounded investigation; Alpha does not reject or suppress the opportunity.","alpha":alpha,"no_external_action":True,"evaluated_at":now})
        oid=f"opportunity_rotation_{RUN}_{lane.lower()}"; wid=f"wo_rotation_{RUN}_{lane.lower()}"
        append_record("opportunities",{"opportunity_id":oid,"title":question,"category":lane,"status":"NEEDS_RESEARCH","source_research_id":rid,"evidence":evidence,"alpha_classification":alpha["classification"],"unknowns":alpha["missing_evidence"],"recommended_next_action":alpha["cheapest_test"],"final_rejection_authority":"ray","created_at":now})
        append_record("work_orders",{"work_order_id":wid,"work_type":"RESEARCH_DERIVED","owner_specialist":owner,"status":"ASSIGNED","route":"RESEARCH_TO_OPPORTUNITY","research_id":rid,"opportunity_id":oid,"action":alpha["cheapest_test"],"authority":"bounded_internal_research","human_approval_required":True,"created_at":now})
        append_record("alpha_outcomes",{"outcome_id":f"outcome_rotation_{RUN}_{lane.lower()}","research_id":rid,"route":owner,"status":"CANDIDATE","classification":alpha["classification"],"opportunity_id":oid,"work_order_id":wid,"created_at":now})
        outputs.append({"lane":lane,"question":question,"sources":evidence,"alpha":alpha,"opportunity_id":oid,"work_order_id":wid,"handoff":owner}); select_next_lane(completed_lane=lane)
    next_lane=select_next_lane()["selected_lane"]; payload={"schema_version":"nexus.research-solution-rotation.v1","run_id":RUN,"created_at":datetime.now(timezone.utc).isoformat(),"outputs":outputs,"next_research_objective":next_lane,"rotation":{"max_consecutive_loops":2,"starvation_protection":True},"alpha_can_reject":False,"alpha_can_suppress_research":False,"final_business_rejection_authority":"RAY","external_action_performed":False}
    ARTIFACT.parent.mkdir(parents=True,exist_ok=True); ARTIFACT.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    REPORT.write_text("# Research solution-seeking rotation\n\n"+json.dumps({"run_id":RUN,"topics":[x["lane"] for x in outputs],"successful_sources":sum(sum(s["status"]=="SUCCESS" for s in x["sources"]) for x in outputs),"opportunities":len(outputs),"work_orders":len(outputs),"handoffs":[x["handoff"] for x in outputs],"next_research_objective":next_lane,"alpha_can_reject":False},indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"artifact":str(ARTIFACT),"report":str(REPORT),"topics":[x["lane"] for x in outputs],"next_research_objective":next_lane,"sources":sum(len(x["sources"]) for x in outputs),"successful_sources":sum(sum(s["status"]=="SUCCESS" for s in x["sources"]) for x in outputs),"opportunities":len(outputs),"work_orders":len(outputs),"handoffs":len(outputs)},indent=2)); return 0
if __name__=="__main__": raise SystemExit(main())
