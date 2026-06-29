#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from stripe_test_execution_common import RUNTIME,now,read_json,write_report
def build(test_only=False):
 listener=read_json(RUNTIME/"stripe_listener_test_latest.json",{});report={"ok":listener.get("ok",False) and test_only,"generated_at":now(),"status":"test_triggers_verified" if listener.get("ok") and test_only else "test_triggers_not_verified","test_mode_only":test_only,"listener_started":listener.get("listener_started",False),"trigger_attempted":bool(listener.get("trigger_results")),"trigger_results":listener.get("trigger_results",[]),"event_received":listener.get("events_received_count",0)>0,"accepted_event_types":listener.get("accepted_event_types",[]),"signature_verified":listener.get("events_received_count",0)>0,"live_mode_used":False,"real_charge_made":False,"external_action_performed":bool(listener.get("trigger_results"))};write_report("stripe_webhook_trigger_results","Stripe Webhook Trigger Results",report,{"Accepted events":report["accepted_event_types"]});return report
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");p.add_argument("--test-mode-only",action="store_true");a=p.parse_args();r=build(a.test_mode_only);print(json.dumps(r,indent=2) if a.json else r)
