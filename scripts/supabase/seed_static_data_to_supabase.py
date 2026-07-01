#!/usr/bin/env python3
"""
Nexus OS v2 — Safe Static Data to Supabase Seed Script

Reads bundled JS static data (via Node.js for reliable parsing),
maps to ACTUAL Supabase schema, deduplicates, validates,
and optionally inserts via service role.

Usage:
  python3 scripts/supabase/seed_static_data_to_supabase.py              # dry-run
  python3 scripts/supabase/seed_static_data_to_supabase.py --execute    # live insert

Requires:
  SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in env (for --execute mode only)
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "ops"))
from same_day_common import now, write_json

REPORT_DIR = ROOT / "reports"
STATIC_DIR = ROOT / "src" / "data"
DEFAULT_TENANT = "tenant_demo_goclear"


def normalize_timestamp(ts: Any) -> str:
    """Normalize a JS ISO timestamp to PostgreSQL-compatible timestamptz.
    PostgreSQL accepts: '2026-06-28 10:00:00+00' or '2026-06-28T10:00:00Z'
    Avoids double-colon issues from Python datetime re-serialization.
    """
    if not ts:
        return now()
    ts = str(ts).strip()
    # If already has timezone offset, keep as-is
    if re.match(r'.+[+-]\d{2}(:\d{2})?$', ts):
        return ts
    # Replace trailing Z with standard offset
    if ts.endswith("Z"):
        return ts[:-1] + "+0000"
    return ts


# ─── JS File Parser (via Node.js) ───

def parse_js_export(file_path: Path, export_name: str) -> Any:
    """Use Node.js to evaluate a JS export and return JSON."""
    js_code = f"""
    import {{ {export_name} }} from '{file_path.resolve()}';
    process.stdout.write(JSON.stringify({export_name}));
    """
    try:
        result = subprocess.run(
            ["node", "--input-type=module", "-e", js_code],
            capture_output=True, text=True, timeout=10,
            cwd=str(ROOT),
        )
        if result.returncode != 0:
            print(f"  WARN: Node.js parse failed for {file_path.name}:{export_name} — {result.stderr.strip()[:200]}")
            return [] if export_name != "revenueStreams" else []
        return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        print(f"  WARN: Failed to parse {file_path.name}:{export_name} — {e}")
        return [] if export_name != "revenueStreams" else []


# ─── Table Mappers ───

def map_ray_review_card(card: dict) -> dict:
    """Map rayReviewData.js card to task_requests row."""
    status_map = {"pending": "requested", "approved": "requested", "rejected": "requested", "held": "requested"}
    return {
        "id": str(uuid.uuid4()),
        "workspace_id": None,
        "task_type": "ray_review_item",
        "requested_by": "nexus_seed",
        "approved_by_ray": None,
        "sensitivity": "public",
        "allowed_data_scope": json.dumps([]),
        "forbidden_data": json.dumps([]),
        "assigned_worker_type": "general_worker",
        "hermes_visibility": "status_only",
        "status": status_map.get(card.get("status", "pending"), "requested"),
        "payload": json.dumps({
            "legacy_id": card.get("id"),
            "title": card.get("title"),
            "category": card.get("category"),
            "riskLevel": card.get("riskLevel"),
            "externalAction": card.get("externalAction"),
            "recommendation": card.get("recommendation"),
            "source": card.get("source"),
            "nextActionCommand": card.get("nextActionCommand"),
            "original_status": card.get("status"),
            "data_source": "static_import",
            "synthetic": True,
        }),
        "result_summary": None,
    }


def map_business_opportunity(opp: dict) -> dict:
    """Map businessOpportunitiesData.js to business_opportunities row."""
    return {
        "id": str(uuid.uuid4()),
        # created_at uses PostgreSQL default now()
        "title": opp.get("title", ""),
        "summary": (opp.get("reason", "") or "")[:500],
        "score": opp.get("score"),
        "status": opp.get("status", "new"),
        "plan": json.dumps({}),
        "payload": json.dumps({
            "legacy_id": opp.get("id"),
            "category": opp.get("category"),
            "revenueRange": opp.get("revenueRange"),
            "confidence": opp.get("confidence"),
            "lane": opp.get("lane"),
            "nextAction": opp.get("nextAction"),
            "convertOptions": opp.get("convertOptions", []),
            "data_source": "static_import",
            "synthetic": True,
        }),
        "tenant_id": DEFAULT_TENANT,
        "external_id": opp.get("id"),
        "category": opp.get("category"),
        "priority": None,
        "risk_level": None,
        "automation_level": None,
        "client_visible": False,
        "approval_required": True,
        "goclear_review_status": "pending",
        "source": "static_import",
        "source_concept": opp.get("lane"),
        "recommended_next_action": opp.get("nextAction"),
    }


def map_research_source(candidate: dict) -> dict:
    """Map researchEngineData.js to research_sources row."""
    return {
        "id": str(uuid.uuid4()),
        "research_run_id": None,
        "source_type": candidate.get("type", "unknown"),
        "title": candidate.get("title", ""),
        "url": None,
        "author": None,
        "published_at": None,
        "accessed_at": now(),
        "snippet": (candidate.get("reason", "") or "")[:500],
        "why_it_matters": candidate.get("nextAction"),
        "confidence": candidate.get("score"),
        "metadata": json.dumps({
            "legacy_id": candidate.get("id"),
            "source": candidate.get("source"),
            "lane": candidate.get("lane"),
            "status": candidate.get("status"),
            "reason": candidate.get("reason"),
            "nextAction": candidate.get("nextAction"),
            "convertOptions": candidate.get("convertOptions", []),
            "data_source": "static_import",
            "synthetic": True,
        }),
    }


def map_monetization_opportunity(offer: dict) -> dict:
    """Map monetizationData.js offers to monetization_opportunities row."""
    return {
        "id": str(uuid.uuid4()),
        "workspace_id": None,
        "title": offer.get("name", ""),
        "source_summary": offer.get("audience"),
        "money_angle": offer.get("nextAction"),
        "status": offer.get("status", "captured"),
        "decision": "needs_review",
        "speed_to_cash": None,
        "fit_with_goclear": None,
        "fit_with_nexus_tools": None,
        "audience_access": None,
        "implementation_effort": None,
        "compliance_risk": None,
        "automation_potential": None,
        "content_potential": None,
        "recurring_revenue_potential": None,
        "confidence": None,
        "overall_score": None,
        "smallest_test": None,
        "missing_tools": json.dumps([]),
        "recommended_jobs": json.dumps([]),
        "metadata": json.dumps({
            "legacy_id": offer.get("id"),
            "price": offer.get("price"),
            "audience": offer.get("audience"),
            "deliverables": offer.get("deliverables", []),
            "stripeStatus": offer.get("stripeStatus"),
            "nextAction": offer.get("nextAction"),
            "data_source": "static_import",
            "synthetic": True,
        }),
    }


def map_client_profile(client: dict) -> dict:
    """Map clientsData.js to client_profiles row."""
    return {
        "id": str(uuid.uuid4()),
        "workspace_id": None,
        "client_label": client.get("name", "Unknown"),
        "current_stage": client.get("stage", "signup_started"),
        "next_required_action": None,
        "due_at": None,
        "days_stuck": 0,
        "progress_percentage": client.get("onboardingReadiness", 0),
        "funding_readiness_impact": 0,
        "revenue_risk_level": "low",
        "ray_review_status": "not_needed",
        "client_visible_status": client.get("overallStatus"),
        "selected_credit_report_source": None,
        "source_selected_at": None,
        "affiliate_partner_id": None,
        "affiliate_url": None,
        "affiliate_disclosure_accepted": False,
        "client_consent_accepted": False,
        "score_available": False,
        "score_source": "unavailable",
        "report_upload_status": "not_started",
        "report_import_status": "not_started",
        "sensitivity": "credit_sensitive",
        "metadata": json.dumps({
            "legacy_id": client.get("id"),
            "name": client.get("name"),
            "email": client.get("email"),
            "status": client.get("status"),
            "paymentStatus": client.get("paymentStatus"),
            "dashboardLiveFlag": client.get("dashboardLiveFlag"),
            "membershipTier": client.get("membershipTier"),
            "subscriptionStatus": client.get("subscriptionStatus"),
            "advisorName": client.get("advisorName"),
            "readinessScores": client.get("readinessScores", {}),
            "documents": client.get("documents", {}),
            "tasks": client.get("tasks", []),
            "messages": client.get("messages", []),
            "reports": client.get("reports", []),
            "data_source": "static_import",
            "synthetic": True,
        }),
        "tenant_id": DEFAULT_TENANT,
        "external_id": client.get("id"),
        "client_id": client.get("id"),
        "category": None,
        "title": client.get("name"),
        "summary": f"Synthetic demo client: {client.get('name')}",
        "status": client.get("status", "active"),
        "score": client.get("onboardingReadiness"),
        "priority": None,
        "risk_level": None,
        "automation_level": None,
        "client_visible": False,
        "approval_required": True,
        "goclear_review_status": "pending",
        "source": "static_import",
        "source_concept": "synthetic_customer",
        "recommended_next_action": None,
    }


def map_nexus_event(table_name: str, row_count: int, receipt_id: str) -> dict:
    """Create a nexus_events seed receipt."""
    return {
        "id": str(uuid.uuid4()),
        "created_at": now(),
        "lane": "system",
        "source": "seed_script",
        "action": "static_data_seeded",
        "status": "completed",
        "title": f"Static data seeded: {table_name}",
        "summary": f"Seeded {row_count} rows into {table_name} from static data. Receipt: {receipt_id}",
        "payload": json.dumps({
            "table": table_name,
            "row_count": row_count,
            "receipt_id": receipt_id,
            "data_source": "static_import",
            "synthetic": True,
        }),
        "visible_to_ray": True,
        "severity": "info",
        "correlation_id": receipt_id,
        "job_id": None,
        "approval_id": None,
    }


# ─── Deduplication ───

def dedupe_by_title(rows: list[dict], title_key: str = "title") -> tuple[list[dict], list[dict]]:
    """Remove duplicate rows by title. Returns (unique, duplicates)."""
    seen = set()
    unique = []
    duplicates = []
    for row in rows:
        title = ""
        if "payload" in row and isinstance(row["payload"], str):
            try:
                payload = json.loads(row["payload"])
                title = payload.get("title", "")
            except (json.JSONDecodeError, TypeError):
                pass
        if not title:
            title = row.get(title_key, "")
        if not title:
            title = row.get("client_label", "")
        key = title.lower().strip()
        if key in seen:
            duplicates.append(row)
        else:
            seen.add(key)
            unique.append(row)
    return unique, duplicates


# ─── Main ───

def build_seed_data(execute: bool = False) -> dict:
    """Build all seed data, validate, and optionally insert."""
    receipt_id = str(uuid.uuid4())[:12]
    results = {"tables": []}

    # ── 1. Ray Review (task_requests) ──
    print("\n[1/5] Ray Review cards → task_requests")
    cards = parse_js_export(STATIC_DIR / "rayReviewData.js", "rayReviewCards")
    print(f"  Parsed {len(cards)} cards from rayReviewData.js")
    mapped_cards = [map_ray_review_card(c) for c in cards]
    unique_cards, dupes_cards = dedupe_by_title(mapped_cards)
    print(f"  Would insert: {len(unique_cards)} | Skipped (dupes): {len(dupes_cards)}")
    results["tables"].append({
        "table": "task_requests",
        "static_source": "rayReviewCards",
        "static_file": "src/data/rayReviewData.js",
        "parsed_count": len(cards),
        "would_insert": len(unique_cards),
        "skipped": len(dupes_cards),
        "skip_reasons": ["duplicate_title"] * len(dupes_cards),
        "filter": "task_type = 'ray_review_item'",
        "requires_service_role": False,
        "rls_policy": "nexus_is_active_admin()",
        "_rows": unique_cards,
    })

    # ── 2. Business Opportunities ──
    print("\n[2/5] Business Opportunities → business_opportunities")
    opps = parse_js_export(STATIC_DIR / "businessOpportunitiesData.js", "businessOpportunities")
    print(f"  Parsed {len(opps)} opportunities")
    mapped_opps = [map_business_opportunity(o) for o in opps]
    unique_opps, dupes_opps = dedupe_by_title(mapped_opps)
    print(f"  Would insert: {len(unique_opps)} | Skipped (dupes): {len(dupes_opps)}")
    results["tables"].append({
        "table": "business_opportunities",
        "static_source": "businessOpportunities",
        "static_file": "src/data/businessOpportunitiesData.js",
        "parsed_count": len(opps),
        "would_insert": len(unique_opps),
        "skipped": len(dupes_opps),
        "skip_reasons": ["duplicate_title"] * len(dupes_opps),
        "requires_service_role": False,
        "rls_policy": "nexus_is_active_admin()",
        "_rows": unique_opps,
    })

    # ── 3. Monetization ──
    print("\n[3/5] Monetization Offers → monetization_opportunities")
    offers = parse_js_export(STATIC_DIR / "monetizationData.js", "offers")
    print(f"  Parsed {len(offers)} offers")
    mapped_offers = [map_monetization_opportunity(o) for o in offers]
    unique_offers, dupes_offers = dedupe_by_title(mapped_offers)
    print(f"  Would insert: {len(unique_offers)} | Skipped (dupes): {len(dupes_offers)}")
    results["tables"].append({
        "table": "monetization_opportunities",
        "static_source": "offers",
        "static_file": "src/data/monetizationData.js",
        "parsed_count": len(offers),
        "would_insert": len(unique_offers),
        "skipped": len(dupes_offers),
        "skip_reasons": ["duplicate_title"] * len(dupes_offers),
        "requires_service_role": False,
        "rls_policy": "nexus_is_active_admin()",
        "_rows": unique_offers,
    })

    # ── 4. Client Profiles ──
    print("\n[4/5] Client Profiles → client_profiles")
    clients = parse_js_export(STATIC_DIR / "clientsData.js", "clientsList")
    print(f"  Parsed {len(clients)} clients")
    mapped_clients = [map_client_profile(c) for c in clients]
    unique_clients, dupes_clients = dedupe_by_title(mapped_clients, title_key="client_label")
    print(f"  Would insert: {len(unique_clients)} | Skipped (dupes): {len(dupes_clients)}")
    results["tables"].append({
        "table": "client_profiles",
        "static_source": "clientsList",
        "static_file": "src/data/clientsData.js",
        "parsed_count": len(clients),
        "would_insert": len(unique_clients),
        "skipped": len(dupes_clients),
        "skip_reasons": ["duplicate_title"] * len(dupes_clients),
        "requires_service_role": False,
        "rls_policy": "nexus_is_active_admin()",
        "_rows": unique_clients,
    })

    # ── 5. Research Sources (service role required) ──
    print("\n[5/5] Research Sources → research_sources (SERVICE ROLE REQUIRED)")
    candidates = parse_js_export(STATIC_DIR / "researchEngineData.js", "researchCandidates")
    print(f"  Parsed {len(candidates)} candidates")
    mapped_candidates = [map_research_source(c) for c in candidates]
    unique_candidates, dupes_candidates = dedupe_by_title(mapped_candidates)
    print(f"  Would insert: {len(unique_candidates)} | Skipped (dupes): {len(dupes_candidates)}")
    results["tables"].append({
        "table": "research_sources",
        "static_source": "researchCandidates",
        "static_file": "src/data/researchEngineData.js",
        "parsed_count": len(candidates),
        "would_insert": len(unique_candidates),
        "skipped": len(dupes_candidates),
        "skip_reasons": ["duplicate_title"] * len(dupes_candidates),
        "requires_service_role": True,
        "rls_policy": "admin_users.active = true (no anon INSERT)",
        "_rows": unique_candidates,
    })

    # ── Seed Receipt ──
    total_insert = sum(t["would_insert"] for t in results["tables"])
    receipt_event = map_nexus_event("all_tables", total_insert, receipt_id)
    results["tables"].append({
        "table": "nexus_events",
        "static_source": "seed_receipt",
        "static_file": "generated",
        "parsed_count": 1,
        "would_insert": 1,
        "skipped": 0,
        "skip_reasons": [],
        "requires_service_role": False,
        "rls_policy": "nexus_is_active_admin()",
        "_rows": [receipt_event],
    })

    # ── Execute if flagged ──
    if execute:
        supabase_url = os.getenv("SUPABASE_URL")
        service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        if not supabase_url or not service_key:
            print("\n  ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required for --execute")
            results["execution"] = {"status": "blocked", "reason": "missing_env_vars"}
            return results

        try:
            from supabase import create_client
            client = create_client(supabase_url, service_key)
        except ImportError:
            print("\n  ERROR: supabase-py not installed. Run: pip install supabase")
            results["execution"] = {"status": "blocked", "reason": "supabase_py_not_installed"}
            return results

        results["execution"] = {"status": "executing", "tables_seeded": []}

        def get_existing_titles(client, table: str) -> set:
            """Fetch existing titles/labels from a table for deduplication."""
            try:
                if table == "task_requests":
                    resp = client.table(table).select("payload").eq("task_type", "ray_review_item").execute()
                    titles = set()
                    for row in (resp.data or []):
                        try:
                            p = json.loads(row.get("payload", "{}"))
                            t = p.get("title", "").lower().strip()
                            if t:
                                titles.add(t)
                        except (json.JSONDecodeError, TypeError):
                            pass
                    return titles
                elif table == "business_opportunities":
                    resp = client.table(table).select("title").execute()
                    return {(r.get("title", "") or "").lower().strip() for r in (resp.data or [])}
                elif table == "monetization_opportunities":
                    resp = client.table(table).select("title").execute()
                    return {(r.get("title", "") or "").lower().strip() for r in (resp.data or [])}
                elif table == "client_profiles":
                    resp = client.table(table).select("client_label").execute()
                    return {(r.get("client_label", "") or "").lower().strip() for r in (resp.data or [])}
                elif table == "research_sources":
                    resp = client.table(table).select("title").execute()
                    return {(r.get("title", "") or "").lower().strip() for r in (resp.data or [])}
                return set()
            except Exception as e:
                print(f"  WARN: Could not fetch existing titles from {table}: {e}")
                return set()

        def filter_existing(rows: list, existing: set, title_key_fn) -> list:
            """Remove rows whose title already exists in the target table."""
            filtered = []
            skipped = 0
            for row in rows:
                title = title_key_fn(row)
                if title.lower().strip() in existing:
                    skipped += 1
                else:
                    filtered.append(row)
            if skipped:
                print(f"  Skipped {skipped} rows already in {table}")
            return filtered

        for table_info in results["tables"]:
            table = table_info["table"]
            rows = table_info.get("_rows", [])
            if not rows:
                continue

            # Deduplicate against existing rows
            existing = get_existing_titles(client, table)
            if existing:
                if table == "task_requests":
                    rows = filter_existing(rows, existing, lambda r: json.loads(r.get("payload", "{}")).get("title", ""))
                elif table == "client_profiles":
                    rows = filter_existing(rows, existing, lambda r: r.get("client_label", ""))
                else:
                    rows = filter_existing(rows, existing, lambda r: r.get("title", ""))

            if not rows:
                print(f"  All rows already exist in {table}, skipping")
                results["execution"]["tables_seeded"].append({"table": table, "inserted": 0, "attempted": 0, "skipped_existing": len(table_info.get("_rows", []))})
                continue

            # Batch insert (50 at a time)
            batch_size = 50
            inserted = 0
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                try:
                    client.table(table).insert(batch).execute()
                    inserted += len(batch)
                    print(f"  Inserted {inserted}/{len(rows)} into {table}")
                except Exception as e:
                    print(f"  ERROR inserting into {table}: {e}")
                    break

            results["execution"]["tables_seeded"].append({
                "table": table,
                "inserted": inserted,
                "attempted": len(rows),
            })

        results["execution"]["status"] = "completed"
    else:
        results["execution"] = None

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed static Nexus data to Supabase")
    parser.add_argument("--execute", action="store_true",
                        help="Actually insert rows (requires SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY)")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON instead of summary")
    args = parser.parse_args()

    print("=" * 60)
    print("NEXUS OS v2 — Static Data → Supabase Seed")
    print(f"Mode: {'LIVE INSERT' if args.execute else 'DRY RUN'}")
    print(f"Time: {now()}")
    print("=" * 60)

    results = build_seed_data(execute=args.execute)

    # Build final report
    report = {
        "ok": True,
        "generated_at": now(),
        "status": "execution_complete" if args.execute and results.get("execution", {}).get("status") == "completed" else ("dry_run_complete" if not args.execute else "execution_failed"),
        "mode": "live_insert" if args.execute else "dry_run",
        "default_tenant": DEFAULT_TENANT,
        "total_would_insert": sum(t["would_insert"] for t in results["tables"] if t["table"] != "nexus_events"),
        "total_skipped": sum(t["skipped"] for t in results["tables"]),
        "tables": [{k: v for k, v in t.items() if k != "_rows"} for t in results["tables"]],
        "execution": results.get("execution"),
        "live_insertion_performed": args.execute,
        "service_role_used": args.execute,
        "external_action_performed": False,
        "next_required_action": "Review dry-run report. If approved, run with --execute flag." if not args.execute else "Verify row counts in Supabase.",
    }

    # Write reports
    report_json_path = REPORT_DIR / "static_to_supabase_seed_dry_run_latest.json"
    report_md_path = REPORT_DIR / "static_to_supabase_seed_dry_run_latest.md"

    write_json(report_json_path, report)

    # Generate markdown
    md_lines = [
        f"# Static-to-Supabase Seed {'Live Insert' if args.execute else 'Dry-Run Report'}",
        "",
        f"**Date:** {now()}",
        f"**Mode:** {'LIVE INSERT' if args.execute else 'DRY RUN'}",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Table | Parsed | Would Insert | Skipped | Service Role |",
        "|-------|--------|--------------|---------|--------------|",
    ]

    for t in results["tables"]:
        if t["table"] == "nexus_events":
            continue
        md_lines.append(
            f"| `{t['table']}` | {t['parsed_count']} | {t['would_insert']} | {t['skipped']} | "
            f"{'Yes' if t['requires_service_role'] else 'No'} |"
        )

    total_insert = sum(t["would_insert"] for t in results["tables"] if t["table"] != "nexus_events")
    total_skipped = sum(t["skipped"] for t in results["tables"])
    md_lines.extend([
        f"| **Total** | | **{total_insert}** | **{total_skipped}** | |",
        "",
        "---",
        "",
        "## Schema Mapping Notes",
        "",
        "The actual Supabase schema uses generic columns (`payload` jsonb, `metadata` jsonb) rather than",
        "the specific columns the original seed plan assumed. This script correctly maps:",
        "",
        "- **task_requests**: `task_type='ray_review_item'`, card data in `payload` jsonb",
        "- **business_opportunities**: `title`, `score`, `status`, `category` as columns; extra fields in `payload` jsonb",
        "- **research_sources**: `source_type`, `title`, `confidence` as columns; extra fields in `metadata` jsonb",
        "- **monetization_opportunities**: `title`, `status`, `decision` as columns; extra fields in `metadata` jsonb",
        "- **client_profiles**: `client_label`, `current_stage`, `progress_percentage` as columns; extra fields in `metadata` jsonb",
        "",
        "---",
        "",
        "## Table Details",
        "",
    ])

    for t in results["tables"]:
        if t["table"] == "nexus_events":
            continue
        md_lines.extend([
            f"### `{t['table']}`",
            "",
            f"- Static source: `{t['static_file']}`",
            f"- Parsed: {t['parsed_count']} records",
            f"- Would insert: {t['would_insert']}",
            f"- Skipped: {t['skipped']}",
            f"- RLS policy: {t['rls_policy']}",
            "",
        ])

    if args.execute and results.get("execution"):
        md_lines.extend(["---", "", "## Execution Result", ""])
        for ts in results["execution"].get("tables_seeded", []):
            md_lines.append(f"- `{ts['table']}`: inserted {ts['inserted']}/{ts['attempted']}")

    report_md_path.write_text("\n".join(md_lines))
    print(f"\nReports written to:")
    print(f"  {report_md_path}")
    print(f"  {report_json_path}")

    if args.json:
        print(json.dumps(report, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
