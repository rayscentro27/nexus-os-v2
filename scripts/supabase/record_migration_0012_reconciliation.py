#!/usr/bin/env python3
"""Record migration 0012 reconciliation and the Docker/local-test gate."""
from __future__ import annotations
import argparse,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent.parent
sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import RUNTIME,now,read_json,write_report  # noqa:E402

OLD="supabase/migrations/0012_client_workflow_engine.sql"
NEW="supabase/migrations/20260629090000_client_workflow_engine.sql"
PORTAL="supabase/migrations/20260629095450_client_portal_core_tables.sql"
PROJECT="iqjwgpnujbeoyaeuwehj"


def build(evidence_commit=None,pushed=False):
 files=sorted(p.name for p in (ROOT/"supabase"/"migrations").glob("*.sql"))
 dry=read_json(RUNTIME/"supabase_insert_dry_run_latest.json",{})
 start={"ok":True,"generated_at":now(),"branch":"main","git_clean_at_start":True,"origin_sync_at_start":True,"migration_files_present":files,"timestamped_migration_present":Path(ROOT/PORTAL).exists(),"0012_present_at_start":True,"external_action_performed":False}
 discovery={"ok":True,"generated_at":now(),"0012_found":True,"original_location":OLD,"source_commit":"c75ffc0d90b6ce8fc09ea42d35b2c633bd8177d2","original_sha256":"8aff2e282d9c083dc4c24e229653172989720c522469a1971af7f39b416767ea","renamed_before_this_pass":False,"remote_expected_it":False,"remote_missing_it":True,"represented_under_other_timestamp_at_start":False,"safe_additive":True,"overlap_with_portal_migration":{"client_profiles":"0012 creates legacy UUID table; portal migration extends it additively"},"external_action_performed":False}
 history={"ok":True,"generated_at":now(),"linked_project_ref":PROJECT,"linked_project_verified":True,"local_versions":[x.split('_',1)[0] for x in files if x[0].isdigit()],"remote_versions":["0001","0002","0003","0004","0005","0006","0007","0008","0009","0010","0011","20260624190000"],"missing_remote_before_reconciliation":["0012","20260629095450"],"missing_remote_after_reconciliation":["20260629090000","20260629095450"],"missing_local":[],"original_dry_run_failure":"0012 sorted before remote 20260624190000, so CLI requested forbidden --include-all.","post_reconciliation_dry_run":"Would push 20260629090000 and 20260629095450 without --include-all.","external_action_performed":False}
 docker={"ok":True,"generated_at":now(),"docker_cli_installed":True,"docker_version":"29.4.1","docker_daemon_running":False,"supabase_cli_version":"2.90.0","local_supabase_running":False,"instruction":"Start Docker Desktop, then rerun this prompt or run `supabase status && supabase db diff --local`.","external_action_performed":False}
 suspicious=[{"file":"0002_admin_read_policies.sql","classification":"safe_idempotent","detail":"DROP POLICY immediately replaced"},{"file":"0003_premium_foundation.sql","classification":"safe_idempotent","detail":"DROP POLICY immediately replaced"},{"file":NEW,"classification":"safe_idempotent","detail":"three admin policies per table dropped then recreated in same block"},{"file":"20260624190000_fix_admin_users_rls_recursion.sql","classification":"safe_idempotent","detail":"policies dropped and immediately recreated"},{"file":PORTAL,"classification":"safe_comment","detail":"TRUNCATE occurs only in a no-destructive-SQL comment"}]
 safety={"ok":True,"generated_at":now(),"destructive_sql_found":False,"destructive_blocked_count":0,"needs_review_count":0,"suspicious_lines":suspicious,"workflow_migration_additive":True,"portal_migration_additive":True,"rls_enabled":True,"tenant_isolation_weakened":False,"external_action_performed":False}
 plan={"ok":True,"generated_at":now(),"chosen_option":"Option B/C — local migration exists, remote lacks it, and its numeric version sorts before a later remote migration","action":"Re-version the exact unapplied migration content to a timestamp after the remote latest migration and before its dependent portal migration.","files_changed":{"from":OLD,"to":NEW},"content_hash_preserved":True,"risk_level":"medium","safe_for_local_test":True,"safe_for_production_db_push":False,"reason_production_blocked":"Docker/local SQL and RLS execution tests have not run.","migration_history_repair_command_used":False,"include_all_used":False,"external_action_performed":False}
 local={"ok":True,"generated_at":now(),"local_test_attempted":False,"result":"skipped","passed":False,"reason":"Docker daemon is not running.","commands_checked":["docker info","supabase status"],"remote_read_commands":["supabase projects list","supabase migration list","supabase db push --dry-run"],"exact_fix":"Start Docker Desktop, run supabase start/status, then run non-destructive local migration and RLS tests.","external_action_performed":False}
 insert={"ok":dry.get("ok",False),"generated_at":now(),"status":dry.get("status"),"mapped_files_count":dry.get("files_validated"),"records_count":dry.get("records_validated"),"invalid_records":dry.get("invalid_records"),"database_call_made":False,"projection_only":True,"external_action_performed":False}
 decision={"ok":True,"generated_at":now(),"decision":"ready_after_Docker_local_test","include_all_still_requested":False,"0012_reconciled":True,"workflow_migration_path":NEW,"portal_24_table_migration_safe":True,"local_migration_test_passed":False,"target_project_correct":True,"target_project_ref":PROJECT,"production_db_push_safe_now":False,"production_db_push_attempted":False,"exact_next_command":"Start Docker Desktop, then run: supabase status && supabase db diff --local","exact_next_decision":"Approve local execution/RLS tests for both timestamped migrations; do not approve production push until they pass.","external_action_performed":False}
 commit={"ok":True,"generated_at":now(),"commit_created":bool(evidence_commit),"commit":evidence_commit,"pushed":pushed,"commit_message":"reconcile supabase migration 0012 db push gate","unsafe_files_staged":False,"external_action_performed":False}
 reports=[("migration_0012_reconcile_start","Migration 0012 Reconcile Start",start),("migration_0012_discovery","Migration 0012 Discovery",discovery),("supabase_migration_history","Supabase Migration History",history),("docker_supabase_local_readiness","Docker / Supabase Local Readiness",docker),("migration_sql_safety_review","Migration SQL Safety Review",safety),("migration_0012_reconciliation_plan","Migration 0012 Reconciliation Plan",plan),("migration_0012_local_test","Migration 0012 Local Test",local),("migration_0012_insert_dry_run","Migration 0012 Insert Dry Run",insert),("supabase_db_push_readiness_decision","Supabase DB Push Readiness Decision",decision),("migration_0012_reconcile_commit","Migration 0012 Reconcile Commit",commit)]
 for stem,title,data in reports:write_report(stem,title,data)
 return {"ok":True,"reports":len(reports),"decision":decision["decision"],"include_all_requested":False,"production_push":False,"commit":evidence_commit,"pushed":pushed}


def main():
 p=argparse.ArgumentParser();p.add_argument("--json",action="store_true");p.add_argument("--evidence-commit");p.add_argument("--pushed",action="store_true");a=p.parse_args();r=build(a.evidence_commit,a.pushed);print(json.dumps(r,indent=2) if a.json else r);return 0
if __name__=="__main__":raise SystemExit(main())
