"""Read-only Supabase control-plane drift snapshot.

This adapter uses the authenticated Supabase CLI for catalog SELECT queries and
Edge Function metadata. It never deploys, writes rows, invokes functions, or
changes project configuration. SQL function bodies are inspected only in-memory
to derive safe booleans and SHA-256 fingerprints; source text is never emitted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT_REF_FILE = REPO_ROOT / "supabase/.temp/project-ref"

# Only SELECT statements. No function is invoked, including SECURITY DEFINER
# functions. The query returns object names, grants, predicates' presence, and
# hashes/booleans about function bodies, never function source or table rows.
CATALOG_SQL = r"""
with funcs as (
  select p.oid, n.nspname, p.proname,
         pg_get_function_identity_arguments(p.oid) as args,
         pg_get_userbyid(p.proowner) as owner,
         p.prosecdef,
         pg_get_functiondef(p.oid) as definition
  from pg_proc p
  join pg_namespace n on n.oid=p.pronamespace
  where n.nspname not in ('pg_catalog','information_schema')
), function_flags as (
  select *, lower(definition) as body
  from funcs
),
triggers as (
  select json_agg(json_build_object(
    'schema', tn.nspname,
    'table', tc.relname,
    'trigger', t.tgname,
    'enabled', case t.tgenabled when 'O' then 'ORIGIN' when 'D' then 'DISABLED'
                 when 'R' then 'REPLICA' else 'ALWAYS' end,
    'function', pn.nspname||'.'||p.proname
  ) order by tn.nspname,tc.relname,t.tgname) as items
  from pg_trigger t
  join pg_class tc on tc.oid=t.tgrelid
  join pg_namespace tn on tn.oid=tc.relnamespace
  join pg_proc p on p.oid=t.tgfoid
  join pg_namespace pn on pn.oid=p.pronamespace
  where not t.tgisinternal
),
event_triggers as (
  select json_agg(json_build_object('name',evtname,'enabled',evtenabled,
    'event',evtevent,'owner',pg_get_userbyid(evtowner)) order by evtname) as items
  from pg_event_trigger
),
function_inventory as (
  select json_agg(json_build_object(
    'name',nspname||'.'||proname,'args',args,'owner',owner,
    'security_definer',prosecdef,
    'anon_execute',has_function_privilege('anon',oid,'execute'),
    'authenticated_execute',has_function_privilege('authenticated',oid,'execute'),
    'service_role_execute',has_function_privilege('service_role',oid,'execute'),
    'definition_sha256',encode(digest(definition,'sha256'),'hex'),
    'mentions_task_requests',body like '%task_requests%',
    'mentions_durable_jobs',body like '%nexus_durable_jobs%',
    'mentions_handoffs',body like '%nexus_department_handoffs%',
    'mentions_credit_jobs',body like '%credit_analysis_jobs%',
    'mentions_http',body ~* '(http|pg_net|net\.http|webhook|functions/v1|functions\.invoke)'
  ) order by nspname,proname,args) as items
  from function_flags
),
control_tables as (
  select json_agg(json_build_object(
    'table',n.nspname||'.'||c.relname,
    'rls',c.relrowsecurity,'force_rls',c.relforcerowsecurity,
    'anon_insert_grant',has_table_privilege('anon',c.oid,'insert'),
    'authenticated_insert_grant',has_table_privilege('authenticated',c.oid,'insert'),
    'service_role_insert_grant',has_table_privilege('service_role',c.oid,'insert'),
    'policies',(select count(*) from pg_policy pol where pol.polrelid=c.oid)
  ) order by n.nspname,c.relname) as items
  from pg_class c join pg_namespace n on n.oid=c.relnamespace
  where c.relkind in ('r','p') and c.relname in (
    'task_requests','nexus_durable_jobs','nexus_department_handoffs',
    'nexus_job_footprints','client_documents','credit_analysis_jobs',
    'credit_document_workflows','credit_workflow_events'
  )
),
policies as (
  select json_agg(json_build_object('table',schemaname||'.'||tablename,
    'name',policyname,'roles',roles,'command',cmd,
    'using_present',coalesce(qual,'')<>'',
    'check_present',coalesce(with_check,'')<>'')
    order by schemaname,tablename,policyname) as items
  from pg_policies where schemaname='public' and tablename in (
    'task_requests','nexus_durable_jobs','nexus_department_handoffs',
    'nexus_job_footprints','client_documents','credit_analysis_jobs',
    'credit_document_workflows','credit_workflow_events'
  )
)
select json_build_object(
  'extensions',(select coalesce(json_agg(extname order by extname),'[]'::json) from pg_extension),
  'automation_schemas',(select coalesce(json_agg(nspname order by nspname),'[]'::json)
    from pg_namespace where nspname in ('cron','net','supabase_functions')),
  'migration_versions',(select coalesce(json_agg(version::text order by version),'[]'::json)
    from supabase_migrations.schema_migrations),
  'database_triggers',coalesce((select items from triggers),'[]'::json),
  'event_triggers',coalesce((select items from event_triggers),'[]'::json),
  'functions',coalesce((select items from function_inventory),'[]'::json),
  'control_tables',coalesce((select items from control_tables),'[]'::json),
  'policies',coalesce((select items from policies),'[]'::json)
) as catalog;
"""


def _run_json(args: list[str], timeout: float = 25.0) -> Any:
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    if result.returncode:
        # Never include CLI output: it can contain untrusted remote values.
        raise RuntimeError(f"{Path(args[0]).name} {args[1]} failed (exit {result.returncode})")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{Path(args[0]).name} returned non-JSON output") from exc


def _run_catalog(project_ref: str) -> dict[str, Any]:
    with tempfile.NamedTemporaryFile("w", suffix=".sql", encoding="utf-8") as sql_file:
        sql_file.write(CATALOG_SQL)
        sql_file.flush()
        payload = _run_json([
            "supabase", "db", "query", "--linked", "--output", "json",
            "--file", sql_file.name,
        ])
    rows = payload.get("rows", [])
    if not rows or not isinstance(rows[0].get("catalog"), dict):
        raise RuntimeError("Supabase catalog query returned no catalog payload")
    return rows[0]["catalog"]


def _run_cron_inventory() -> list[dict[str, Any]]:
    # Only called after the catalog proves pg_cron is installed and cron schema
    # exists. Never return the command text because it can contain credentials.
    query = (
        "select coalesce(json_agg(json_build_object("
        "'jobid',jobid,'schedule',schedule,'active',active,"
        "'command_md5',md5(command)) order by jobid),'[]'::json) as jobs from cron.job;"
    )
    payload = _run_json(["supabase", "db", "query", "--linked", "--output", "json", query])
    rows = payload.get("rows", [])
    if not rows:
        return []
    return rows[0].get("jobs", []) or []


def _local_migrations(repo_root: Path) -> set[str]:
    result: set[str] = set()
    for path in (repo_root / "supabase/migrations").glob("*.sql"):
        match = re.match(r"(\d+)_", path.name)
        if match:
            result.add(match.group(1))
    return result


def _stable_hash(value: Any) -> str:
    blob = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def collect(project_ref: str, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    catalog = _run_catalog(project_ref)
    functions_payload = _run_json([
        "supabase", "functions", "list", "--project-ref", project_ref, "--output", "json",
    ])
    if not isinstance(functions_payload, list):
        raise RuntimeError("Supabase Edge Function inventory was not a list")
    local_function_names = {
        p.name for p in (repo_root / "supabase/functions").iterdir()
        if p.is_dir() and p.name != "_shared"
    }
    deployed = sorted(({
        "name": row.get("name"),
        "status": row.get("status"),
        "version": row.get("version"),
        "verify_jwt": row.get("verify_jwt"),
        "updated_at": row.get("updated_at"),
        "bundle_sha256": row.get("ezbr_sha256"),
    } for row in functions_payload), key=lambda row: str(row["name"]))
    deployed_names = {str(row["name"]) for row in deployed if row.get("name")}
    local_migrations = _local_migrations(repo_root)
    remote_migrations = set(catalog.get("migration_versions", []))
    cron_jobs: list[dict[str, Any]] = []
    if "pg_cron" in catalog.get("extensions", []) and "cron" in catalog.get("automation_schemas", []):
        cron_jobs = _run_cron_inventory()
    db_signature = {
        key: catalog.get(key, []) for key in (
            "extensions", "automation_schemas", "database_triggers", "event_triggers",
            "functions", "control_tables", "policies",
        )
    }
    edge_signature = deployed
    work_functions = [
        item for item in catalog.get("functions", [])
        if any(item.get(flag) for flag in (
            "mentions_task_requests", "mentions_durable_jobs", "mentions_handoffs", "mentions_credit_jobs"
        ))
    ]
    work_function_names = {item.get("name") for item in work_functions}
    trigger_work_paths = [
        item for item in catalog.get("database_triggers", [])
        if item.get("function") in work_function_names
    ]
    return {
        "schema_version": 1,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "project_ref": project_ref,
        "access_path": "authenticated_supabase_cli_management_api_and_linked_read_only_sql",
        "mode": "READ_ONLY",
        "database": {
            **catalog,
            "cron_jobs": cron_jobs,
            "cron_job_count": len(cron_jobs),
            "active_cron_job_count": sum(1 for item in cron_jobs if item.get("active")),
            "webhook_related_triggers": [
                item for item in catalog.get("database_triggers", [])
                if re.search(r"webhook|http|pg_net", str(item.get("trigger", "") + " " + item.get("function", "")), re.I)
            ],
            "work_creation_functions": work_functions,
            "triggered_work_creation_paths": trigger_work_paths,
            "database_trigger_count": len(catalog.get("database_triggers", [])),
            "event_trigger_count": len(catalog.get("event_triggers", [])),
            "security_definer_function_count": sum(
                1 for item in catalog.get("functions", []) if item.get("security_definer")
            ),
            "network_marked_function_names": [
                item["name"] for item in catalog.get("functions", []) if item.get("mentions_http")
            ],
            "cron_extension_present": "pg_cron" in catalog.get("extensions", []),
            "pg_net_extension_present": "pg_net" in catalog.get("extensions", []),
            "database_webhook_extension_present": (
                "pg_net" in catalog.get("extensions", [])
                or "supabase_functions" in catalog.get("automation_schemas", [])
            ),
            "signature_sha256": _stable_hash(db_signature),
        },
        "migrations": {
            "local_count": len(local_migrations),
            "remote_count": len(remote_migrations),
            "local_only": sorted(local_migrations - remote_migrations),
            "remote_only": sorted(remote_migrations - local_migrations),
            "in_sync": local_migrations == remote_migrations,
        },
        "edge_functions": {
            "deployed_count": len(deployed),
            "deployed": deployed,
            "source_only": sorted(local_function_names - deployed_names),
            "remote_only": sorted(deployed_names - local_function_names),
            "signature_sha256": _stable_hash(edge_signature),
        },
        "authority": {
            "can_create_business_work": False,
            "can_call_providers": False,
            "can_deploy_functions": False,
            "can_enable_runtime": False,
            "can_modify_database": False,
        },
        "limitations": [
            "Edge Function secrets are not read; only source-code environment-variable names are outside this adapter.",
            "The adapter does not inspect provider-side webhooks or account-console Auth hook settings.",
            "Cron command text is never returned; only its MD5 fingerprint is recorded when pg_cron is installed.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-ref", default=None)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    project_ref = args.project_ref
    if not project_ref and PROJECT_REF_FILE.exists():
        project_ref = PROJECT_REF_FILE.read_text(encoding="utf-8").strip()
    if not project_ref or not re.fullmatch(r"[a-z0-9]{10,30}", project_ref):
        parser.error("a valid --project-ref or supabase/.temp/project-ref is required")
    try:
        payload = collect(project_ref, args.repo_root.resolve())
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        # Error class only; do not echo untrusted CLI/database output.
        payload = {
            "schema_version": 1,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "project_ref": project_ref,
            "mode": "READ_ONLY",
            "status": "COLLECTION_FAILED",
            "error_class": type(exc).__name__,
            "authority": {
                "can_create_business_work": False,
                "can_call_providers": False,
                "can_deploy_functions": False,
                "can_enable_runtime": False,
                "can_modify_database": False,
            },
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"status": payload["status"], "error_class": payload["error_class"]}))
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {
        "status": "COLLECTED",
        "migration_drift": not payload["migrations"]["in_sync"],
        "deployed_edge_functions": payload["edge_functions"]["deployed_count"],
        "remote_only_edge_functions": len(payload["edge_functions"]["remote_only"]),
        "database_trigger_count": payload["database"]["database_trigger_count"],
        "authority": payload["authority"],
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
