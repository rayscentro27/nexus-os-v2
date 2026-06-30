#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from monetization_common import SUPABASE_READY,now,write_json,write_report
def build():
 stages=[{"stage":"research_source","status":"active_internal"},{"stage":"lead_reactivation_draft","status":"draft_ready"},{"stage":"Ray_approval","status":"required"},{"stage":"Stripe_test_checkout","status":"open_unpaid"},{"stage":"payment_confirmation","status":"approval_gated"},{"stage":"synthetic_onboarding","status":"dry_run_ready"},{"stage":"client_delivery","status":"blocked_until_synthetic_journey_passes"},{"stage":"subscription_upgrade","status":"draft"}];write_json(SUPABASE_READY/"revenue_recovery_funnel_latest.json",stages);report={"ok":True,"generated_at":now(),"status":"revenue_recovery_funnel_ready","stages":len(stages),"active_internal_stages":3,"external_stages_gated":5,"external_action_performed":False};write_report("revenue_recovery_funnel","Revenue Recovery Funnel",report,{"Stages":stages});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
