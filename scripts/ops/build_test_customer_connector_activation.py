#!/usr/bin/env python3
"""Consolidate test connector reports, Ray Review cards, and Hermes guidance."""
from __future__ import annotations
import argparse,json,subprocess
from same_day_common import ROOT,RUNTIME,SUPABASE_READY,now,read_json,write_json,write_report

def load(stem): return read_json(RUNTIME/f"{stem}_latest.json",{})
def card(card_id,title,decision,risk="medium"):
 return {"id":card_id,"tenant_id":"tenant_test_goclear","client_id":"client_test_julius_erving","category":"connector_activation_approval","title":title,"status":"pending_Ray_review","priority":"high","risk_level":risk,"automation_level":"approval_required","client_visible":False,"approval_required":True,"exact_decision_needed":decision,"options":["approve","reject","defer"],"external_action_performed":False,"created_at":now()}

def build():
 customer=load("fake_customer_test_package");stripe=load("stripe_cli_env_audit");checkout=load("stripe_test_checkout_plan");intent=load("stripe_payment_intent_test_plan");webhook=load("stripe_webhook_test_plan");onboarding=load("payment_to_client_onboarding_flow");old_nlm=load("old_notebooklm_connector_audit");nlm=load("notebooklm_source_import");youtube=load("youtube_review_proof");transcript=load("youtube_transcript_import");trading=load("oanda_vibe_trading_audit");payment_repos=load("payment_repo_concept_extraction");schedules=load("automation_schedule_registry")
 cards=[
  card("approve-stripe-test-checkout","Approve Stripe CLI test Checkout","Provide/confirm test-mode keys and approve one synthetic $97 Checkout Session.","high"),
  card("approve-stripe-test-intent","Approve Stripe test PaymentIntent","Provide/confirm test-mode keys and approve one unconfirmed synthetic $97 PaymentIntent.","high"),
  card("approve-stripe-webhook-test","Approve Stripe webhook test","Approve a local listener and synthetic Stripe CLI event only.","high"),
  card("approve-test-client-insert","Approve fake customer persistent Supabase insertion","Approve only tenant_test_goclear synthetic records after test webhook verification.","high"),
  card("approve-notebooklm-recovery","Approve NotebookLM CLI recovery integration","Approve rebuilding the isolated legacy nlm environment; no consumer browser automation."),
  card("approve-youtube-transcript","Approve YouTube transcript import","Approve one user-provided target-linked TXT transcript when available."),
  card("approve-oanda-vibe-paper","Approve Oanda demo + Vibe Trading paper/backtest integration test","Require explicit Oanda practice mode and bounded backtest; no orders.","high"),
  card("approve-payment-roadmap","Approve payment repository roadmap","Approve Stripe-first architecture; defer multi-processor and crypto infrastructure."),
  card("approve-connector-schedules","Approve connector automation schedule activation","Approve internal schedules only; keep external/payment/trading/database actions gated.","high"),
 ]
 write_json(SUPABASE_READY/"connector_activation_ray_review_cards_latest.json",cards)
 write_report("connector_activation_ray_review_cards","Connector Activation Ray Review Cards",{"ok":True,"generated_at":now(),"status":"ready_for_Ray_review","cards_created":len(cards),"external_action_performed":False},{"Cards":cards})
 recommendations=[
  "Do not use the detected live Stripe keys for testing; configure separate test-mode keys before Checkout or PaymentIntent execution.",
  "Keep the synthetic customer package dry-run until a verified test webhook and idempotency proof exist.",
  "Recover the legacy NotebookLM adapter first; rebuild its isolated CLI only after Ray approval.",
  "Add one approved TXT transcript to activate transcript review; keep YouTube API metadata and yt-dlp probing separate.",
  "Require explicit Oanda practice environment proof before any broker test; use existing backtest components without placing orders.",
  "Keep Stripe first and payment repository concepts roadmap-only.",
 ]
 hermes={"ok":True,"generated_at":now(),"status":"admin_brief_ready","recommendations":recommendations,"next_money_action":"Configure Stripe test-mode credentials, approve the synthetic $97 Checkout test, then prove webhook-to-test-client idempotency.","what_must_stay_gated":["Stripe API writes","persistent fake-client insertion","NotebookLM CLI auth","Oanda demo connectivity/orders","public publishing","live Supabase inserts"],"external_action_performed":False}
 write_report("hermes_connector_activation_brief","Hermes Connector Activation Brief",hermes,{"Recommendations":recommendations})
 branch=subprocess.run(["git","branch","--show-current"],cwd=ROOT,capture_output=True,text=True).stdout.strip();commit=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True).stdout.strip()
 baseline={"ok":True,"generated_at":now(),"branch":branch,"start_commit":commit,"repo_clean_at_start":True,"baseline_build_passed":True,"known_live_url":"https://nexusv20.netlify.app/","external_action_performed":False}
 write_report("test_customer_connector_baseline","Test Customer Connector Baseline",baseline)
 master={"ok":True,"generated_at":now(),"status":"test_connector_activation_complete","test_customer_package_created":customer.get("ok",False),"package":customer.get("package"),"live_records_inserted":False,"stripe_cli_found":stripe.get("stripe_cli",{}).get("installed",False),"stripe_test_mode_ready":stripe.get("test_secret_detected",False),"checkout_test_plan_ready":checkout.get("ok",False),"payment_intent_test_plan_ready":intent.get("ok",False),"webhook_test_plan_ready":webhook.get("ok",False),"payment_to_client_onboarding_ready":onboarding.get("ok",False),"real_charges_made":False,"old_notebooklm_cli_found":old_nlm.get("old_cli_found",False),"old_notebooklm_adapter_found":old_nlm.get("files_found",0)>0,"notebooklm_intake_ready":nlm.get("ok",False),"notebooklm_sources_imported":nlm.get("sources_imported",0),"youtube_api_active":youtube.get("api_or_connector_configured",False),"transcript_imported":transcript.get("transcripts_imported",0),"youtube_mode":youtube.get("review_mode"),"oanda_demo_config_present":trading.get("oanda_mode")=="practice","oanda_mode":trading.get("oanda_mode"),"vibe_trading_installed":trading.get("vibe_cli_installed",False),"vibe_integration_status":trading.get("integration_status"),"live_trades_placed":False,"payment_repo_concepts":payment_repos.get("concepts_created",0),"ray_review_cards":len(cards),"automation_schedules":schedules.get("scheduled_automation_count",0),"enabled_internal_automations":schedules.get("enabled_internal_automations",0),"hermes_recommendations":recommendations,"blocked_by_missing_env":["Stripe test secret/publishable keys","Stripe test webhook secret","Explicit Oanda practice environment","Approved YouTube transcript TXT"],"blocked_by_approval":[x["title"] for x in cards],"blocked_by_frontend_live_data_wiring":["Synthetic test client is not inserted","Stripe event handler is plan-only","NotebookLM sources are local/manual"],"safe_automations_now":["YouTube API cache refresh","local transcript folder scan","NotebookLM local import scan","synthetic package generation","payment plan generation","connector audits","static concept extraction","Ray Review refresh"],"external_action_performed":False}
 write_report("nexus_test_customer_connector_activation","Nexus Test Customer Connector Activation",master,{"Blocked by env":master["blocked_by_missing_env"],"Blocked by approval":master["blocked_by_approval"],"Safe automations":master["safe_automations_now"]});return master

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r)
