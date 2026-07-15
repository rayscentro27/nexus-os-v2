#!/usr/bin/env python3
"""Bounded, idempotent replay for one synthetic tester persona."""

import argparse
import json
import os
import ssl
import subprocess
import sys
import urllib.parse
from pathlib import Path

import certifi

ROOT = Path(__file__).resolve().parents[2]
SSL = ssl.create_default_context(cafile=certifi.where())
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reset_synthetic_credit_case import envfile, query, resolve_scope, rest  # noqa: E402

FIXTURE_VERSION = "controlled-pilot-v1"


def count(url, key, table, filters):
    return len(query(url, key, table, "*", filters))


def run_seed(persona, env):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/testers/seed_credit_workflow_fixtures.py"), "--persona", persona],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError("base synthetic fixture seed failed")


def run_pilot_state(persona, env):
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/testers/ensure_synthetic_pilot_state.py"), persona],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError("controlled pilot state persistence failed")
    try:
        return json.loads(result.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError) as error:
        raise RuntimeError("controlled pilot state returned invalid summary") from error


def verify_state(url, key, scope, require_followup=True):
    common = {"tenant_id": f"eq.{scope['tenant_id']}", "client_id": f"eq.{scope['client_id']}"}
    docs = query(url, key, "client_documents", "id,title", common)
    parsers = query(url, key, "credit_report_parser_results", "id,document_id", common)
    canonical = query(url, key, "credit_canonical_accounts", "id,document_id", common)
    # The strategy match table is verified directly before recommendations.
    strategy_matches = query(url, key, "credit_strategy_matches", "id", common)
    recommendations = query(url, key, "credit_strategy_recommendations", "id,client_visible", common)
    comparisons = query(url, key, "credit_report_comparison_runs", "id", common)
    readiness = query(url, key, "credit_readiness_history", "id", common)
    exceptions = query(url, key, "credit_strategy_exceptions", "id,status", common)
    drafts = query(url, key, "credit_strategy_drafts", "id,status", common)
    decisions = query(url, key, "credit_strategy_client_decisions", "id,decision", common)
    active_jobs = query(url, key, "credit_analysis_jobs", "id,status", {**common, "status": "in.(queued,processing)"})
    initial_title = f"synthetic_persona_{scope['persona']}_three_bureau_report_v3.pdf"
    followup_title = f"synthetic_persona_{scope['persona']}_three_bureau_report_followup_v3.pdf"
    has_initial = any(row.get("title") == initial_title for row in docs)
    has_followup = any(row.get("title") == followup_title for row in docs)
    required = {
        "initial_document": has_initial,
        "followup_document": has_followup if require_followup else True,
        "parser_results": len(parsers) >= (2 if require_followup else 1),
        "canonical_accounts": len(canonical) >= (2 if require_followup else 1),
        "recommendation": len(recommendations) >= 1,
        "strategy_match": len(strategy_matches) >= 1,
        "comparison": len(comparisons) >= 1 if require_followup else True,
        "readiness_history": len(readiness) >= 1 if require_followup else True,
        "draft": scope["persona"] == "b" or len(drafts) >= 1,
        "exception": scope["persona"] != "b" or len(exceptions) >= 1,
        "decision": scope["persona"] == "b" or len(decisions) >= 1,
        "no_active_duplicate_jobs": len(active_jobs) == 0,
    }
    if not all(required.values()):
        failed = ", ".join(key for key, value in required.items() if not value)
        raise RuntimeError(f"state verification failed: {failed}")
    return {
        "persona": scope["persona"].upper(),
        "fixture_version": FIXTURE_VERSION,
        "documents": len(docs),
        "parser_results": len(parsers),
        "canonical_accounts": len(canonical),
        "recommendations": len(recommendations),
        "strategy_matches": len(strategy_matches),
        "drafts": len(drafts),
        "decisions": len(decisions),
        "exceptions": len(exceptions),
        "comparison_runs": len(comparisons),
        "readiness_history": len(readiness),
        "active_jobs": len(active_jobs),
        "verified": True,
    }


def main():
    parser = argparse.ArgumentParser(description="Replay one synthetic tester persona")
    parser.add_argument('--persona', required=True, choices=['a', 'b', 'c'])
    parser.add_argument('--full', action='store_true', help='initial plus follow-up replay')
    parser.add_argument('--initial-only', action='store_true')
    parser.add_argument('--follow-up-only', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    if sum(bool(value) for value in (args.full, args.initial_only, args.follow_up_only)) > 1:
        print("ERROR: choose only one replay mode")
        return 2
    mode = "full" if args.full or not (args.initial_only or args.follow_up_only) else "initial" if args.initial_only else "follow-up"

    env = {**envfile(ROOT / ".env"), **envfile(ROOT / ".env.e2e.local"), **os.environ}
    url = env.get("SUPABASE_URL") or env.get("VITE_SUPABASE_URL")
    key = env.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("ERROR: server-side Supabase credentials unavailable")
        return 1

    persona = args.persona
    try:
        scope = resolve_scope(url, key, persona)
        print(f"=== Synthetic replay: Persona {persona.upper()} ===")
        print(f"Mode: {'DRY RUN' if args.dry_run else 'VERIFY' if args.verify else 'EXECUTE'}; workflow: {mode}")
        print("Scope proof: exact synthetic Auth identity → one goclear client membership")
        if args.dry_run:
            print("Planned: selected-persona seed, persisted comparison/readiness state, and bounded verification")
            return 0
        if args.verify:
            summary = verify_state(url, key, scope, require_followup=mode != "initial")
            print(json.dumps(summary))
            return 0

        if mode in {"full", "initial"}:
            run_seed(persona, env)
        # The controlled state helper is idempotent and also creates the
        # follow-up fixture/comparison for full replay.
        state = run_pilot_state(persona, env)
        summary = verify_state(url, key, scope, require_followup=mode != "initial")
        print(json.dumps({"replay": state, "verification": summary}))
        print(f"Replay complete: Persona {persona.upper()}; no active duplicate jobs")
        return 0
    except Exception as error:
        print(f"ERROR: Persona {persona.upper()} replay failed: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
