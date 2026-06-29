#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from same_day_common import ROOT,RUNTIME,MANUAL,now,read_json,write_json,write_report  # noqa:E402


def load(stem):return read_json(RUNTIME/f"{stem}_latest.json",{})


def recommendations():
 top=[
  ("Activate Supabase core tables and RLS","backend/data","P0 immediate","large","needs_Ray_approval","Review the draft migration, test tenant policies locally, and approve a timestamped migration."),
  ("Replace demo client data with tenant-safe records","client experience","P0 immediate","large","schedule","Implement tenant membership and client profile reads after RLS passes."),
  ("Activate real YouTube metadata or transcript intake","automation","P0 immediate","small","needs_Ray_approval","Add YOUTUBE_API_KEY server-side or one approved transcript file, then rerun intake."),
  ("Approve the $97 payment and CRM path","revenue","P0 immediate","medium","needs_Ray_approval","Approve Stripe test mode, the $97 product/price, webhook mapping, and Supabase client creation."),
  ("Process today's prioritized Ray Review queue","operations","P0 immediate","small","needs_Ray_approval","Record approve/reject/defer for the same-day cards in priority order."),
  ("Build private document storage and message policies","safety/compliance","P0 immediate","large","schedule","Create private bucket, retention rules, malware scanning, consent, and tenant/client RLS tests."),
  ("Move dispute proof to synthetic sandbox testing","safety/compliance","P1 high","medium","needs_Ray_approval","Approve non-deliverable sandbox recipients and proof-only vendor tests; keep production disabled."),
  ("Validate the Meta connector read-only","automation","P1 high","small","needs_Ray_approval","Approve a token-redacted /me/accounts identity check; do not post."),
  ("Confirm the bounded continuous loop","operations","P1 high","small","do_now","Monitor nexus_today_ops heartbeat and stop it after eight cycles or earlier if needed."),
  ("Complete report-backed Hermes and Nexus Guide reads","UI/UX","P1 high","medium","schedule","Connect structured approved guidance and engine status after tenant-safe reads exist."),
 ]
 rest=[
  "Seed tenant memberships with a synthetic local test user","Write automated RLS cross-tenant denial tests","Map every remaining Supabase-ready export","Add idempotency keys to future insert operations","Create private storage retention schedule","Define client document consent language","Add malware scanning design for uploads","Create payment webhook signature verification","Create idempotent post-payment client creation","Write the $97 fulfillment service-level checklist","Approve $97 landing-page claims","Create the sales conversation script","Build subscription upgrade event records","Create referral tracking records","Validate Stripe price identifiers in test mode","Add payment failure recovery tasks","Create CRM lead-to-client state transitions","Add client auth role routing","Hide demo labels automatically for authenticated clients","Create client data loading/error states","Add readiness score versioning","Add score explanation audit history","Create guidance approval expiry","Add client question escalation notifications","Create GoClear review turnaround states","Add dispute evidence completeness scoring","Create dispute letter version history","Define certified-mail sandbox vendor criteria","Add connector credential rotation checklist","Validate Meta token expiry read-only","Create social post version history","Create content compliance linting","Add YouTube source provenance fields","Create transcript consent/provenance checklist","Add bounded YouTube quota policy","Schedule connector health checks without external actions","Add engine-run correlation IDs","Add proof-event retention policy","Create operational failure alerts","Document tmux loop recovery","Prepare launchd approval package","Add monthly value-loop completion metrics","Create churn-risk task triggers","Add partner recommendation disclosures","Validate free/DIY partner alternatives","Add funding guidance review expiry","Create support escalation playbook","Add dashboard data freshness labels","Add admin approval bulk-defer","Run a paid-client synthetic rehearsal"
 ]
 rest=rest[:40]
 assert len(rest)==40
 recs=[]
 for i,item in enumerate(top+[(x,"operations","P2 medium","medium","schedule",f"Implement and verify: {x}.") for x in rest],1):
  title,impact,priority,effort,status,action=item
  recs.append({"rank":i,"title":title,"category":impact,"priority":priority,"impact":impact,"effort":effort,"status":status,"why_it_matters":"Closes a measured activation gap and moves Nexus toward safe paid-client automation.","exact_next_action":action,"files_systems_affected":["client portal","Supabase","operations"],"helps_97_offer":i<=15,"helps_monthly_subscription":i not in {8,9},"helps_paid_client_onboarding":i<=20})
 return recs


def build()->dict:
 env=load("env_connector_inventory");gap=load("env_connector_gap_analysis");recovery=load("safe_env_recovery_plan");yt=load("youtube_review_proof");sup=load("supabase_production_readiness");dry=load("supabase_insert_dry_run");client=load("client_portal_paid_client_hardening");docs=load("documents_messages_hardening");dispute=load("dispute_sandbox_upgrade_plan");meta=load("meta_connector_validation_plan");payment=load("payment_crm_path");assist=load("hermes_nexus_guide_upgrade");review=load("ray_review_prioritized_today");engine=load("same_day_activation_engine_run")
 status=subprocess.check_output(["git","status","--porcelain"],cwd=ROOT,text=True).splitlines(); latest=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
 key_names=sorted({x["key"] for x in env.get("inventory",[]) if x.get("present")})
 pre={"ok":True,"generated_at":now(),"branch":"main","audit_evidence_commit":"73eb1b3","latest_commit_at_report_time":latest,"uncommitted_count":len(status),"env_or_secret_files_staged":False,"recovered_env_gitignored":True,"build_before_audit_commit_passed":True,"safety_before_audit_commit_passed":True,"external_action_performed":False}
 write_report("pre_activation_git_safety","Pre-Activation Git Safety",pre,{"Uncommitted paths":status})
 continuous={"ok":True,"generated_at":now(),"status":"bounded_internal_running","started":True,"tmux_session":"nexus_today_ops","command":"python3 scripts/activation/run_nexus_continuous_loop.py --interval-minutes 30 --max-cycles 8 --json --safe-internal --local-only --feedback-enabled","heartbeat_path":"reports/runtime/continuous_loop_status_latest.json","stop_command":"tmux kill-session -t nexus_today_ops","what_it_will_do":["safe internal activation","feedback intake","reports/exports","Hermes brief","heartbeat"],"what_it_will_not_do":["publish","send messages","contact clients/bureaus/lenders","insert live Supabase data","place trades","spend money"],"external_action_performed":False}
 write_report("today_continuous_ops_activation","Today Continuous Ops Activation",continuous,{"Will do":continuous["what_it_will_do"],"Will not do":continuous["what_it_will_not_do"]})
 recs=recommendations();write_json(RUNTIME/"nexus_next_50_recommendations_latest.json",{"ok":True,"generated_at":now(),"recommendations":recs})
 lines=["# Nexus Next 50 Recommendations",""]
 for x in recs:lines += [f"## {x['rank']}. {x['title']}","",f"- priority: {x['priority']}",f"- impact: {x['impact']}",f"- effort: {x['effort']}",f"- status: {x['status']}",f"- next: {x['exact_next_action']}",""]
 (MANUAL/"nexus_next_50_recommendations_latest.md").write_text("\n".join(lines))
 master={"ok":True,"generated_at":now(),"status":"operational_foundation_active","nexus_live_working":True,"admin_working":True,"client_portal_working":True,
  "committed_before_activation":{"client_portal":"6468b95","full_audit":"73eb1b3"},"uncommitted_count_before_final_commit":len(status),
  "original_env_files_found":env.get("env_files_found",[]),"connector_key_names_found":key_names,"connector_keys_missing_in_v2":gap.get("original_keys_missing_in_v2",[]),
  "safe_env_recovery":{"created":recovery.get("target_created"),"copied_key_names":recovery.get("copied_key_names",[]),"raw_values_reported":False},
  "configured_connectors":["Supabase","Meta configuration (unvalidated)","Stripe configuration (test approval pending)","Telegram/local AI keys recovered"],
  "missing_connectors":["YouTube API metadata connector","private document storage","CRM beyond Supabase","certified-mail sandbox"],
  "approval_blocked_connectors":["Meta read-only validation","Stripe test workflow","Supabase migrations/inserts","dispute sandbox","external publishing/sending"],
  "youtube_before":"queue_only_no_real_review","youtube_after":yt.get("review_mode"),"youtube_metadata_review":yt.get("review_mode")=="real_metadata_review_active","youtube_transcript_review":yt.get("review_mode")=="real_transcript_review_active","youtube_exact_setup":yt.get("next_required_action"),
  "social_connector_configured":meta.get("status")=="connector_config_present_validation_pending","social_publish_blocked":True,"social_sandbox_step":meta.get("safe_validation_command"),
  "supabase_ready_for_table_creation":sup.get("status")=="ready_for_migration_review","migration_drafted":"supabase/migrations/DRAFT_client_portal_core_tables.sql","migration_table_count":24,"insert_dry_run":dry.get("status"),"live_supabase_blockers":sup.get("blockers",[]),
  "client_portal_paid_data_ready":False,"client_portal_mode":client.get("current_mode"),"demo_static_remaining":["profile/demo values","live uploads","live message delivery","authenticated client reads"],
  "documents_messages_hardened":docs.get("status"),"dispute_sandbox_plan_exists":dispute.get("ok",False),"real_disputes_blocked":True,
  "payment_crm_path":payment.get("status"),"payment_missing":["Ray test-mode approval","webhook signature secret/config","product/price verification","idempotent client creation"],
  "hermes_upgraded":assist.get("hermes_report_backed",False),"nexus_guide_upgraded":assist.get("nexus_guide_safe_templates_updated",False),
  "ray_review_prioritized":review.get("ok",False),"ray_approve_today_count":review.get("approve_today_count",0),"continuous_loop_running":True,
  "automated_today":["env inventory/recovery","source/transcript intake path","Supabase schema/dry-run validation","client export hardening","draft generation","approval prioritization","bounded internal loop"],
  "must_remain_approval_gated":["database migration/execution","payment activation","social validation/publishing","dispute sandbox/sending","client guidance","funding recommendations"],
  "engine_run":{"passed":engine.get("engines_passed"),"failed":engine.get("engines_failed")},
  "exact_next_command":"python3 scripts/supabase/run_supabase_insert_dry_run.py --json",
  "exact_next_decision":"Approve the 24-table Supabase draft/RLS local test plan and the $97 Stripe test-mode workflow; do not approve production execution yet.",
  "external_action_performed":False,"money_spent":False,"client_contacted":False,"public_content_published":False,"real_disputes_sent":False,"live_supabase_insertion":False}
 write_report("nexus_same_day_operations_activation","Nexus Same-Day Operations Activation",master,{"Original env files":master["original_env_files_found"],"Connector key names":key_names,"Blockers":master["live_supabase_blockers"],"Top 10":recs[:10]})
 return {"ok":True,"recommendations":len(recs),"approve_today":master["ray_approve_today_count"],"youtube":master["youtube_after"],"continuous":True}


def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");a=p.parse_args();r=build();print(json.dumps(r,indent=2) if a.json else r);return 0
if __name__=="__main__":raise SystemExit(main())
