#!/usr/bin/env python3
"""All-Night Internal Test Runner.

Runs every safe internal dry-run process in cycles. Order: automation/access/vault/workflow checks,
then market/revenue checks, then the overnight MONEY OPPORTUNITY engine + creative drafts, then the
Hermes final brief + Ray morning agenda. Everything is internal/report-only — no external action.

    python3 scripts/night_run/run_all_night_internal_tests.py --dry-run --cycles 1 --interval-minutes 0 --json
"""
from __future__ import annotations
import argparse, json, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import night_run_model as nm  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent

# Ordered phases.
PHASES = [
    ("automation_access_vault_workflow", [
        "scripts/automation/generate_automation_control_report.py",
        "scripts/automation/verify_automation_policy.py",
        "scripts/automation/verify_high_risk_guards.py",
        "scripts/ai_access/verify_ai_department_access.py",
        "scripts/ai_access/verify_agent_runtime.py",
        "scripts/client_vault/verify_client_vault_contract.py",
        "scripts/client_workflow/verify_client_workflow_policy.py",
        "scripts/client_workflow/generate_client_workflow_report.py",
        "scripts/client_workflow/generate_stuck_client_report.py",
    ]),
    ("market_revenue_checks", [
        "scripts/night_run/generate_goclear_subscription_market_research.py",
        "scripts/night_run/generate_online_business_bank_affiliate_research.py",
        "scripts/night_run/generate_revenue_streams.py",
        "scripts/partners/generate_partner_offers_report.py",
        "scripts/partners/verify_partner_offer_config.py",
        "scripts/partners/generate_affiliate_waiting_room_report.py",
        "scripts/revenue/generate_goclear_offer_pricing_report.py",
        "scripts/revenue/generate_first_offer_launch_gate.py",
    ]),
    ("money_opportunity_engine", [
        "scripts/research/generate_money_opportunity_research.py",
        "scripts/revenue/generate_money_opportunity_scoreboard.py",
        "scripts/revenue/generate_money_opportunity_launch_plan.py",
        "scripts/creative/generate_overnight_creative_asset_queue.py",
        "scripts/creative/generate_best_money_opportunity_creative_package.py",
    ]),
    ("hermes_final_brief_and_agenda", [
        "scripts/hermes/generate_money_opportunity_brief.py",
        "scripts/night_run/generate_hermes_executive_brief.py",
        "scripts/hermes/generate_ray_morning_money_agenda.py",
        "scripts/night_run/generate_approval_and_blocked.py",
    ]),
]

RUNTIME = ROOT / "reports" / "runtime" / "all_night_run_latest.json"
MANUAL = ROOT / "reports" / "manual_publish" / "all_night_run_latest.md"


def run_one(rel: str) -> dict:
    try:
        proc = subprocess.run([sys.executable, str(ROOT / rel), "--dry-run", "--json"],
                              capture_output=True, text=True, timeout=120)
        try:
            ok = json.loads(proc.stdout).get("ok")
        except Exception:
            ok = proc.returncode == 0
        return {"script": rel, "exit_code": proc.returncode, "ok": bool(ok),
                "error": proc.stderr.strip()[-200:] if proc.returncode != 0 else ""}
    except Exception as e:  # noqa: BLE001
        return {"script": rel, "exit_code": -1, "ok": False, "error": str(e)[-200:]}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", default=True)
    p.add_argument("--cycles", type=int, default=1)
    p.add_argument("--interval-minutes", type=float, default=0)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    cycles_out = []
    cycles = max(1, min(args.cycles, 50))
    for c in range(cycles):
        phase_results = []
        for phase_name, scripts in PHASES:
            results = [run_one(s) for s in scripts]
            phase_results.append({"phase": phase_name, "results": results,
                                  "ran_ok": sum(1 for r in results if r["ok"]), "total": len(results)})
        failed = [r for ph in phase_results for r in ph["results"] if not r["ok"]]
        cycles_out.append({"cycle": c + 1, "phases": phase_results, "failed": failed,
                           "ok": len(failed) == 0})
        if c + 1 < cycles and args.interval_minutes > 0:
            time.sleep(args.interval_minutes * 60)

    total = sum(ph["total"] for cy in cycles_out for ph in cy["phases"])
    ran_ok = sum(ph["ran_ok"] for cy in cycles_out for ph in cy["phases"])
    all_failed = [f for cy in cycles_out for f in cy["failed"]]
    report = {
        "ok": len(all_failed) == 0,
        "title": "All-Night Internal Test Run",
        "generated_at": nm.now(),
        "dry_run": True,
        "cycles": cycles_out,
        "counts": {"cycles": cycles, "scripts_per_cycle": total // cycles if cycles else 0,
                   "total_runs": total, "ran_ok": ran_ok, "failed": len(all_failed)},
        "summary": f"All-night run: {cycles} cycle(s), {ran_ok}/{total} script runs ok. "
                   + ("All green." if not all_failed else f"{len(all_failed)} failed."),
        "safety": nm.SAFETY,
    }
    RUNTIME.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME.write_text(json.dumps(report, indent=2))
    lines = [f"# {report['title']}", "", f"- generated_at: {report['generated_at']}", f"- ok: {report['ok']}",
             f"- cycles: {cycles} · runs: {total} · ran_ok: {ran_ok} · failed: {len(all_failed)}",
             "- external_action: false · money_spent: false · level_3_blocked: true", ""]
    for cy in cycles_out:
        lines.append(f"## Cycle {cy['cycle']} ({'ok' if cy['ok'] else 'FAILED'})")
        for ph in cy["phases"]:
            lines.append(f"- {ph['phase']}: {ph['ran_ok']}/{ph['total']}")
        if cy["failed"]:
            lines += [f"  - FAILED {f['script']}: {f['error']}" for f in cy["failed"]]
    MANUAL.parent.mkdir(parents=True, exist_ok=True)
    MANUAL.write_text("\n".join(lines) + "\n")
    print(json.dumps(report, indent=2) if args.json else report["summary"])
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
