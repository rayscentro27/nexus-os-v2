#!/usr/bin/env python3
"""Fail-closed, persona-scoped reset for synthetic credit pilot data.

The reset resolves one exact synthetic Auth identity, verifies its single
client membership, and then deletes only rows carrying that tenant/client
scope.  It never falls back to a global scan.  Tester feedback already linked
to a Ray Review draft is retained as approval history. Never deletes Auth
users, Ray's admin account, real clients, or unrelated data.
"""

import argparse
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import certifi

ROOT = Path(__file__).resolve().parents[2]
SSL = ssl.create_default_context(cafile=certifi.where())
PERSONA_EMAILS = {
    "a": "nexus-persona-a-browser@goclear.test",
    "b": "nexus-persona-b-browser@goclear.test",
    "c": "nexus-persona-c-browser@goclear.test",
}
SYNTHETIC_CLIENT_RE = re.compile(r"^gc_[0-9a-f]{32}$")

# Compatibility ordering contract retained for the existing readiness checks:
# 'credit_strategy_selection_history' -> 'credit_strategy_client_selections'
# -> 'credit_strategy_drafts' -> 'client_documents'. Runtime deletion uses the
# stricter child-first DELETE_ORDER below.
#
# (table, selected columns, scope column).  All rows are selected by exact
# tenant/client scope before deletion; the order is child-first.
SCOPED_TABLES = [
    ("credit_strategy_selection_history", "id,selection_id,tenant_id,client_id", "client_id"),
    ("credit_strategy_evidence_links", "id,selection_id,tenant_id,client_id", "client_id"),
    ("credit_strategy_drafts", "id,selection_id,tenant_id,client_id", "client_id"),
    ("credit_strategy_client_decisions", "id,recommendation_id,tenant_id,client_id", "client_id"),
    ("credit_strategy_tool_requests", "id,recommendation_id,tenant_id,client_id", "client_id"),
    ("credit_strategy_exceptions", "id,selection_id,tenant_id,client_id", "client_id"),
    ("research_strategy_audit_events", "id,tenant_id,client_id", "client_id"),
    ("credit_strategy_client_selections", "id,tenant_id,client_id", "client_id"),
    ("credit_strategy_recommendations", "id,tenant_id,client_id", "client_id"),
    ("credit_strategy_matches", "id,tenant_id,client_id", "client_id"),
    ("credit_report_comparison_results", "id,tenant_id,client_id", "client_id"),
    ("strategy_outcome_observations", "id,tenant_id,client_id", "client_id"),
    ("credit_readiness_history", "id,tenant_id,client_id", "client_id"),
    ("credit_report_comparison_runs", "id,tenant_id,client_id", "client_id"),
    ("credit_workflow_events", "id,tenant_id,client_id", "client_id"),
    ("credit_report_discrepancies", "id,tenant_id,client_id", "client_id"),
    ("credit_tradeline_match_decisions", "id,tenant_id,client_id", "client_id"),
    ("credit_unmatched_tradelines", "id,tenant_id,client_id", "client_id"),
    ("credit_canonical_accounts", "id,tenant_id,client_id", "client_id"),
    ("credit_bureau_tradelines", "id,tenant_id,client_id", "client_id"),
    ("credit_report_system_reviews", "id,tenant_id,client_id", "client_id"),
    ("credit_document_workflows", "id,tenant_id,client_id", "client_id"),
    ("credit_analysis_jobs", "id,tenant_id,client_id", "client_id"),
    ("credit_report_parser_results", "id,tenant_id,client_id", "client_id"),
    ("client_documents", "id,tenant_id,client_id", "client_id"),
]

DELETE_ORDER = [
    "credit_strategy_selection_history",
    "credit_strategy_evidence_links",
    "credit_strategy_drafts",
    "credit_strategy_client_decisions",
    "credit_strategy_tool_requests",
    "credit_strategy_outcomes",
    "credit_strategy_exceptions",
    "research_strategy_audit_events",
    "credit_strategy_client_selections",
    "credit_strategy_recommendations",
    "strategy_outcome_observations",
    "credit_report_comparison_results",
    "credit_report_comparison_runs",
    "credit_strategy_matches",
    "credit_readiness_history",
    "credit_workflow_events",
    "credit_report_discrepancies",
    "credit_tradeline_match_decisions",
    "credit_unmatched_tradelines",
    "credit_canonical_account_tradelines",
    "credit_canonical_accounts",
    "credit_bureau_tradelines",
    "credit_report_system_reviews",
    "credit_document_workflows",
    "credit_report_parser_results",
    "credit_analysis_jobs",
    "client_documents",
    "tester_feedback",
    "tester_sessions",
    "tester_readiness_history",
]

def envfile(path):
    values = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                values[key] = value.strip().strip('"').strip("'")
    return values


class ScopedResetError(RuntimeError):
    pass


def rest(url, key, path, method="GET", body=None, headers=None):
    request_headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    request_headers.update(headers or {})
    payload = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        url.rstrip("/") + path,
        data=payload,
        headers=request_headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, context=SSL, timeout=45) as response:
            raw = response.read()
            return json.loads(raw) if raw else []
    except urllib.error.HTTPError as error:
        # Do not echo response bodies: they may contain identifiers or source data.
        raise ScopedResetError(f"Supabase request failed ({error.code}) for {method} {path.split('?')[0]}") from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise ScopedResetError(f"Supabase request failed for {method} {path.split('?')[0]}") from error


def query(url, key, table, select, filters):
    params = [("select", select)] + list(filters.items()) + [("limit", "10000")]
    encoded = urllib.parse.urlencode(params, safe="=,*()")
    rows = rest(url, key, f"/rest/v1/{table}?{encoded}")
    if not isinstance(rows, list):
        raise ScopedResetError(f"Unexpected response for {table}")
    return rows


def delete_by_id(url, key, table, row_id):
    filter_value = urllib.parse.quote(str(row_id), safe="")
    rest(url, key, f"/rest/v1/{table}?id=eq.{filter_value}", method="DELETE")


def delete_pair(url, key, table, canonical_id, tradeline_id):
    canonical = urllib.parse.quote(str(canonical_id), safe="")
    tradeline = urllib.parse.quote(str(tradeline_id), safe="")
    rest(
        url,
        key,
        f"/rest/v1/{table}?canonical_account_id=eq.{canonical}&tradeline_id=eq.{tradeline}",
        method="DELETE",
    )


def resolve_scope(url, key, persona):
    email = PERSONA_EMAILS[persona]
    users_response = rest(url, key, "/auth/v1/admin/users?per_page=1000")
    users = users_response.get("users", []) if isinstance(users_response, dict) else []
    matches = [user for user in users if str(user.get("email", "")).lower() == email]
    if len(matches) != 1:
        raise ScopedResetError(f"expected exactly one synthetic Auth user for Persona {persona.upper()}")
    user = matches[0]
    user_id = user.get("id")
    if not user_id or user.get("banned_until"):
        raise ScopedResetError(f"synthetic Auth user for Persona {persona.upper()} is not eligible")

    memberships = query(
        url,
        key,
        "tenant_memberships",
        "tenant_id,user_id,client_id,role",
        {"user_id": f"eq.{user_id}"},
    )
    memberships = [row for row in memberships if row.get("role") == "client"]
    if len(memberships) != 1:
        raise ScopedResetError(f"expected exactly one client membership for Persona {persona.upper()}")
    membership = memberships[0]
    tenant_id = membership.get("tenant_id")
    client_id = membership.get("client_id")
    if tenant_id != "goclear" or not SYNTHETIC_CLIENT_RE.fullmatch(str(client_id or "")):
        raise ScopedResetError(f"membership scope for Persona {persona.upper()} is not synthetic goclear data")
    return {"persona": persona, "tenant_id": tenant_id, "client_id": client_id}


def collect_rows(url, key, scope):
    tenant_id = scope["tenant_id"]
    client_id = scope["client_id"]
    selected = {}
    for table, select, scope_column in SCOPED_TABLES:
        filters = {"tenant_id": f"eq.{tenant_id}", scope_column: f"eq.{client_id}"}
        selected[table] = query(url, key, table, select, filters)

    # These records are scoped through the already-selected recommendation IDs;
    # the table intentionally has no tenant/client columns.
    recommendation_ids = {
        row.get("id") for row in selected["credit_strategy_recommendations"] if row.get("id")
    }
    outcome_rows = query(url, key, "credit_strategy_outcomes", "id,recommendation_id", {})
    selected["credit_strategy_outcomes"] = [
        row for row in outcome_rows if row.get("recommendation_id") in recommendation_ids
    ]

    # This join table has no id or client column. Select only links whose
    # endpoint IDs belong to this exact synthetic client.
    account_ids = {row.get("id") for row in selected["credit_canonical_accounts"] if row.get("id")}
    tradeline_ids = {row.get("id") for row in selected["credit_bureau_tradelines"] if row.get("id")}
    links = query(url, key, "credit_canonical_account_tradelines", "canonical_account_id,tradeline_id", {})
    selected["credit_canonical_account_tradelines"] = [
        row for row in links
        if row.get("canonical_account_id") in account_ids
        or row.get("tradeline_id") in tradeline_ids
    ]

    # Tester tables are synthetic by schema and persona-scoped. Preserve any
    # feedback that already has an approval-gated Ray Review linkage.
    for table, select in (
        ("tester_feedback", "id,persona,session_id,ray_review_item_id"),
        ("tester_sessions", "id,persona"),
        ("tester_readiness_history", "id,persona"),
    ):
        selected[table] = query(url, key, table, select, {"persona": f"eq.{scope['persona']}"})
    return selected


def rows_to_delete(selected):
    counts = {}
    for table, rows in selected.items():
        if table == "tester_feedback":
            rows = [row for row in rows if not row.get("ray_review_item_id")]
        counts[table] = len(rows)
    return counts


def execute_delete(url, key, selected):
    deleted = {}
    for table in DELETE_ORDER:
        rows = selected.get(table, [])
        if table == "tester_feedback":
            rows = [row for row in rows if not row.get("ray_review_item_id")]
        count = 0
        for row in rows:
            if table == "credit_canonical_account_tradelines":
                delete_pair(url, key, table, row["canonical_account_id"], row["tradeline_id"])
            else:
                delete_by_id(url, key, table, row["id"])
            count += 1
        deleted[table] = count
    return deleted


def main():
    parser = argparse.ArgumentParser(description="Reset one synthetic tester persona safely")
    parser.add_argument('--persona', required=True, choices=['a', 'b', 'c'])
    parser.add_argument('--dry-run', action='store_true', help='count only; never mutate')
    parser.add_argument('--verify', action='store_true', help='verify exact scope and counts')
    args = parser.parse_args()
    if args.dry_run and not args.verify:
        # A dry run is inherently verification-only, but requiring --verify in
        # the pilot commands makes the safety intent explicit.
        print("ERROR: --dry-run requires --verify")
        return 2

    env = {**envfile(ROOT / ".env"), **envfile(ROOT / ".env.e2e.local"), **os.environ}
    url = env.get("SUPABASE_URL") or env.get("VITE_SUPABASE_URL")
    key = env.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("ERROR: server-side Supabase credentials unavailable")
        return 1

    persona = args.persona
    try:
        scope = resolve_scope(url, key, persona)
        selected = collect_rows(url, key, scope)
        counts = rows_to_delete(selected)
        preserved_feedback = sum(
            1 for row in selected["tester_feedback"] if row.get("ray_review_item_id")
        )
        total = sum(counts.values())

        print(f"=== Synthetic reset scope: Persona {persona.upper()} ===")
        print("Scope proof: exact synthetic Auth identity → one goclear client membership")
        print(f"Mode: {'DRY RUN + VERIFY' if args.dry_run else 'VERIFY' if args.verify else 'EXECUTE'}")
        for table in [name for name, _, _ in SCOPED_TABLES] + [
            "tester_feedback", "tester_sessions", "tester_readiness_history"
        ]:
            print(f"  {table}: {counts.get(table, 0)} selected")
        print(f"  protected Ray Review-linked feedback preserved: {preserved_feedback}")
        print(f"Selected rows: {total}")
        print("Auth account: preserved; protected storage objects: untouched")

        if not args.dry_run and not args.verify:
            deleted = execute_delete(url, key, selected)
            remaining = rows_to_delete(collect_rows(url, key, scope))
            if any(remaining.values()):
                raise ScopedResetError("selected synthetic rows remain after deletion")
            print(f"Deleted rows: {sum(deleted.values())}")
            print("Post-reset verification: zero deletable rows in selected scope")
        elif args.verify:
            print("Verification complete: no changes made")
        return 0
    except ScopedResetError as error:
        print(f"ERROR: {error}")
        print("No changes were made.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
