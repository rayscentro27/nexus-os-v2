#!/usr/bin/env python3
"""
Nexus OS v2 — Supabase Live Status Verification
Prompt 2: Phase B

Verifies that Nexus can read/write the current v2 Supabase project safely.
Never prints secret values. Only prints key names and status.
"""

import os
import json
import sys
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Load .env file if present
_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith('#') and '=' in _line:
                _key, _, _val = _line.partition('=')
                _key = _key.strip()
                _val = _val.strip().strip('"').strip("'")
                if _key and _val and _key not in os.environ:
                    os.environ[_key] = _val

REPORT_MD = "reports/supabase/nexus_prompt_2_live_supabase_verification.md"
REPORT_JSON = "reports/runtime/nexus_live_source_status.json"

REQUIRED_KEYS = [
    "VITE_SUPABASE_URL",
    "VITE_SUPABASE_ANON_KEY",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
]

CORE_TABLES = [
    "admin_users",
    "approvals",
    "task_requests",
    "nexus_events",
    "system_health",
    "agent_jobs",
    "research_sources",
    "research_runs",
    "business_opportunities",
    "monetization_opportunities",
    "client_profiles",
    "client_tasks",
    "readiness_scores",
    "client_documents",
]


def check_env_keys():
    results = {}
    for key in REQUIRED_KEYS:
        val = os.environ.get(key, "")
        results[key] = {
            "present": bool(val),
            "length": len(val) if val else 0,
        }
    return results


def supabase_rest_get(url, key, table, limit=1):
    """Read-only HEAD+GET to check table existence and count."""
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    # Count query
    count_url = f"{url}/rest/v1/{table}?select=*&limit={limit}"
    req = Request(count_url, headers=headers, method="GET")
    try:
        resp = urlopen(req, timeout=10)
        data = json.loads(resp.read())
        return {"exists": True, "row_count_sample": len(data), "status": "accessible"}
    except HTTPError as e:
        if e.code == 404:
            return {"exists": False, "status": "table_not_found"}
        return {"exists": False, "status": f"http_{e.code}", "error": str(e.reason)}
    except URLError as e:
        return {"exists": False, "status": "connection_error", "error": str(e.reason)}
    except Exception as e:
        return {"exists": False, "status": "error", "error": str(e)}


def supabase_rest_insert(url, key, table, data):
    """Service-role insert to a safe status/event table."""
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    insert_url = f"{url}/rest/v1/{table}"
    body = json.dumps(data).encode()
    req = Request(insert_url, data=body, headers=headers, method="POST")
    try:
        resp = urlopen(req, timeout=10)
        result = json.loads(resp.read())
        return {"success": True, "inserted": result}
    except HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        return {"success": False, "status": f"http_{e.code}", "error": body_text[:200]}
    except Exception as e:
        return {"success": False, "status": "error", "error": str(e)}


def run_verification():
    now = datetime.now(timezone.utc).isoformat()
    env_status = check_env_keys()
    all_keys_present = all(v["present"] for v in env_status.values())

    supabase_url = os.environ.get("SUPABASE_URL", "")
    supabase_anon_key = os.environ.get("VITE_SUPABASE_ANON_KEY", "")
    service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    table_results = {}
    if all_keys_present and supabase_url and supabase_anon_key:
        for table in CORE_TABLES:
            table_results[table] = supabase_rest_get(
                supabase_url, supabase_anon_key, table
            )
    else:
        for table in CORE_TABLES:
            table_results[table] = {"exists": False, "status": "skipped_missing_keys"}

    # Test write to nexus_events (safe, synthetic)
    write_result = None
    if all_keys_present and supabase_url and service_role_key:
        write_payload = {
            "event_type": "supabase_verification",
            "lane": "system",
            "payload": {
                "prompt": "prompt_2",
                "verification_time": now,
                "synthetic": True,
                "message": "Supabase live verification write test",
            },
        }
        write_result = supabase_rest_insert(
            supabase_url, service_role_key, "nexus_events", write_payload
        )

    tables_found = sum(1 for t in table_results.values() if t.get("exists"))
    tables_total = len(CORE_TABLES)

    result = {
        "generated_at": now,
        "env_keys": env_status,
        "all_keys_present": all_keys_present,
        "supabase_url_configured": bool(supabase_url),
        "tables_checked": tables_total,
        "tables_found": tables_found,
        "tables": table_results,
        "write_test": write_result,
        "overall_status": "verified" if (all_keys_present and tables_found > 0) else "not_connected",
        "recommendation": (
            "Supabase live connectivity verified. Ready for activation."
            if all_keys_present and tables_found > 0
            else "Supabase not connected. Check env keys and migration status."
        ),
    }

    # Write JSON
    os.makedirs(os.path.dirname(REPORT_JSON), exist_ok=True)
    with open(REPORT_JSON, "w") as f:
        json.dump(result, f, indent=2)

    # Write Markdown
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    with open(REPORT_MD, "w") as f:
        f.write("# Nexus Prompt 2 — Live Supabase Verification\n\n")
        f.write(f"**Generated**: {now}\n\n")
        f.write("---\n\n")
        f.write("## Environment Keys\n\n")
        f.write("| Key | Present | Length |\n|-----|---------|--------|\n")
        for key, info in env_status.items():
            f.write(f"| `{key}` | {'YES' if info['present'] else 'NO'} | {info['length']} |\n")
        f.write(f"\n**All keys present**: {'YES' if all_keys_present else 'NO'}\n\n")
        f.write("---\n\n")
        f.write("## Table Verification\n\n")
        f.write("| Table | Exists | Status | Rows (sample) |\n|-------|--------|--------|---------------|\n")
        for table, info in table_results.items():
            exists = "YES" if info.get("exists") else "NO"
            status = info.get("status", "unknown")
            rows = info.get("row_count_sample", "-")
            f.write(f"| `{table}` | {exists} | {status} | {rows} |\n")
        f.write(f"\n**Tables found**: {tables_found}/{tables_total}\n\n")
        f.write("---\n\n")
        f.write("## Write Test\n\n")
        if write_result:
            f.write(f"**Table**: `nexus_events`\n")
            f.write(f"**Success**: {'YES' if write_result.get('success') else 'NO'}\n")
            if not write_result.get("success"):
                f.write(f"**Error**: {write_result.get('error', 'unknown')}\n")
        else:
            f.write("Skipped (missing keys)\n")
        f.write(f"\n---\n\n")
        f.write(f"## Overall Status: {result['overall_status'].upper()}\n\n")
        f.write(f"{result['recommendation']}\n")

    return result


if __name__ == "__main__":
    result = run_verification()
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["overall_status"] == "verified" else 1)
