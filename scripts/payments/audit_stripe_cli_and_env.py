#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from payment_test_common import ROOT, env_data, now, stripe_cli, write_report

def build():
    cli=stripe_cli(); env=env_data()
    legacy=[str(p) for p in [ROOT.parent/"nexuslive/src/services/stripeService.ts", ROOT.parent/"nexuslive/netlify/functions/stripe-webhook.js", ROOT.parent/"nexuslive/supabase/functions/stripe-webhook/index.ts"] if p.exists()]
    ready=cli["installed"] and env["test_secret_detected"] and not env["live_secret_detected"]
    report={"ok":True,"generated_at":now(),"status":"stripe_test_mode_ready_for_Ray_approval" if ready else "stripe_test_setup_incomplete",
            "stripe_cli":cli,"env_key_presence":env["presence"],"test_secret_detected":env["test_secret_detected"],
            "test_publishable_detected":env["test_publishable_detected"],"live_key_detected_but_not_used":env["live_secret_detected"] or env["live_publishable_detected"],
            "legacy_payment_files":legacy,"raw_values_included":False,"stripe_api_called":False,"real_charge_created":False,"external_action_performed":False}
    write_report("stripe_cli_env_audit","Stripe CLI and Environment Audit",report,{"Legacy files":legacy}); return report
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
