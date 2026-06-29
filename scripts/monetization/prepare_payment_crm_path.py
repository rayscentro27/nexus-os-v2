#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent.parent;sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import SUPABASE_READY,env_presence,now,write_json,write_report  # noqa:E402


def build()->dict:
 names=["STRIPE_SECRET_KEY","STRIPE_PUBLISHABLE_KEY","VITE_STRIPE_PUBLISHABLE_KEY","VITE_STRIPE_PRICE_PRO","VITE_STRIPE_PRICE_ELITE","AIRTABLE_API_KEY","HUBSPOT_ACCESS_TOKEN"]
 present=env_presence(*names);stripe=present["STRIPE_SECRET_KEY"] and (present["STRIPE_PUBLISHABLE_KEY"] or present["VITE_STRIPE_PUBLISHABLE_KEY"]);crm=present["AIRTABLE_API_KEY"] or present["HUBSPOT_ACCESS_TOKEN"]
 payment=[{"id":"payment-demo-97","tenant_id":"tenant_demo_goclear","client_id":"client_pending_creation","category":"payment_status","title":"$97 Readiness Review payment","summary":"Payment record placeholder; no charge or live link created.","status":"setup_pending","priority":"high","risk_level":"medium","automation_level":"approval_required","client_visible":False,"approval_required":True,"amount_cents":9700,"currency":"usd","provider":"stripe_candidate" if stripe else "manual_approved_method_pending","external_payment_performed":False,"created_at":now()}]
 onboarding=[{"id":f"onboarding-{i+1}","tenant_id":"tenant_demo_goclear","client_id":"client_pending_creation","category":"post_payment_onboarding","title":title,"status":"template_ready","priority":"high","risk_level":"low","automation_level":"admin_review_required","client_visible":False,"approval_required":True,"created_at":now()} for i,title in enumerate(["Verify approved payment status","Create tenant-scoped client profile","Assign $97 review workflow","Request minimum documents with consent","Schedule GoClear manual review","Publish approved tasks to client portal"])]
 offer=[{"id":"offer-readiness-review-97","tenant_id":"tenant_demo_goclear","client_id":"not_applicable","category":"offer","title":"$97 Funding / Credit Readiness Review","summary":"Educational readiness assessment covering personal credit factors, business profile, documentation, blockers, and a GoClear-reviewed next-action plan. No approval, score, deletion, or funding outcome is guaranteed.","status":"ready_for_Ray_review","price_cents":9700,"approval_required":True,"external_action_performed":False,"created_at":now()}]
 write_json(SUPABASE_READY/"payment_status_latest.json",payment);write_json(SUPABASE_READY/"client_onboarding_after_payment_latest.json",onboarding);write_json(SUPABASE_READY/"readiness_review_offer_latest.json",offer)
 report={"ok":True,"generated_at":now(),"status":"configuration_found_approval_pending" if stripe else "payment_config_missing","payment_key_presence":present,"raw_values_included":False,"stripe_configuration_detected":stripe,"crm_configuration_detected":crm,"live_payment_link_created":False,"money_charged":False,"manual_payment_fallback":["Ray selects an approved payment method","operator verifies status manually","create tenant-scoped client only after verified payment","log proof event"],"stripe_setup_checklist":["verify server-side secret and publishable key pairing","create/confirm $97 product and price","configure webhook signature secret","map paid event to idempotent client creation","test in Stripe test mode","Ray approves production switch"],"crm_next_step":"Use Supabase client_profiles as initial CRM system of record" if not crm else "Review existing CRM connector before use","ray_review_card":"Approve payment provider, $97 scope, test-mode checkout, and post-payment client creation workflow.","external_action_performed":False,"summary":"Payment keys were safely checked and a complete $97 onboarding path was prepared without charging or creating a live link."}
 write_report("payment_crm_path","Payment / CRM Path",report,{"Manual fallback":report["manual_payment_fallback"],"Stripe checklist":report["stripe_setup_checklist"],"Onboarding":onboarding});return report


def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r);return 0
if __name__=="__main__":raise SystemExit(main())
