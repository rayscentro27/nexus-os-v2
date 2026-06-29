#!/usr/bin/env python3
"""Extract static payment architecture concepts; does not fetch or execute repositories."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ops"))
from same_day_common import ROOT,SUPABASE_READY,now,read_json,write_json,write_report  # noqa:E402
def build():
 targets=read_json(ROOT/"configs/payment_repo_targets.json",{}).get("targets",[]);concepts=[]
 for target in targets:
  for i,title in enumerate(target.get("concepts",[]),1):
   concepts.append({"id":f"payment-concept-{target['id']}-{i}","tenant_id":"tenant_demo_goclear","client_id":"not_applicable","category":"payment_repo_concept","title":title,"summary":f"Architecture concept from static reference {target['name']}; no code imported.","status":"research_only","priority":"high" if title in {"idempotency","webhook reliability","PCI boundaries","tokenization"} else "medium","risk_level":"medium","automation_level":"admin_review_required","client_visible":False,"approval_required":True,"source":target["url"],"source_concept":target["id"],"recommended_next_action":"Compare with Stripe-first Nexus design; require license/security review before adaptation.","created_at":now()})
 recommendations=[{"id":"payment-stack-stripe-first","title":"Keep Stripe as first operational processor","phase":"now","decision":"Stripe test Checkout, verified webhooks, idempotent onboarding"},{"id":"payment-stack-orchestration-later","title":"Evaluate processor abstraction later","phase":"later","decision":"Use Hyperswitch concepts only after paid volume justifies complexity"},{"id":"payment-stack-crypto-later","title":"Defer crypto checkout","phase":"later","decision":"BTCPay concepts remain roadmap-only"},{"id":"payment-stack-pci-boundary","title":"Keep card data outside Nexus","phase":"now","decision":"Hosted checkout/tokenization only"}]
 cards=[{"id":"approve-payment-repo-roadmap","tenant_id":"tenant_demo_goclear","client_id":"not_applicable","category":"approval_card","title":"Approve Stripe-first payment repository roadmap","status":"pending_Ray_review","priority":"high","risk_level":"medium","approval_required":True,"exact_decision_needed":"Approve Stripe first; defer multi-processor and crypto infrastructure.","external_action_performed":False,"created_at":now()}]
 write_json(SUPABASE_READY/"payment_repo_concepts_latest.json",concepts);write_json(SUPABASE_READY/"payment_stack_recommendations_latest.json",recommendations);write_json(SUPABASE_READY/"payment_repo_approval_cards_latest.json",cards)
 report={"ok":True,"generated_at":now(),"status":"static_concept_extraction_complete","targets":len(targets),"concepts_created":len(concepts),"recommendations_created":len(recommendations),"approval_cards_created":len(cards),"repositories_installed":False,"containers_started":False,"github_network_access_performed":False,"external_action_performed":False}
 write_report("payment_repo_concept_extraction","Payment Repository Concept Extraction",report,{"Targets":targets,"Recommendations":recommendations});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
