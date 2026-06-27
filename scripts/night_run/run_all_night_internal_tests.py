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
sys.path.insert(0, str(ROOT / "scripts" / "research"))
import money_opportunity_model as mo  # noqa: E402

CYCLE_HISTORY = ROOT / "reports" / "runtime" / "overnight_money_cycle_history_latest.jsonl"

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


def cycle_summary(cycle_number: int, started_at: str, phase_results: list) -> dict:
    """Per-cycle summary appended to the cycle-history JSONL. Includes the ranked opportunity list."""
    ranked = mo.ranked()
    scripts_run = sum(ph["total"] for ph in phase_results)
    scripts_passed = sum(ph["ran_ok"] for ph in phase_results)
    approval_items = len(mo.by_type("ray_review_approval_item"))
    return {
        "cycle_number": cycle_number,
        "started_at": started_at,
        "completed_at": nm.now(),
        "scripts_run": scripts_run,
        "scripts_passed": scripts_passed,
        "scripts_failed": scripts_run - scripts_passed,
        "top_opportunity": ranked[0]["title"],
        "fastest_to_launch": mo.fastest_to_launch()["title"],
        "lowest_risk": mo.lowest_risk()["title"],
        "best_affiliate": max(mo.needs_affiliate_approval(), key=lambda o: o["scores"]["affiliate_potential"])["title"],
        "best_landing_page": max(ranked, key=lambda o: o["scores"]["landing_page_potential"])["title"],
        "best_social_video": max(ranked, key=lambda o: max(o["scores"]["tiktok_potential"], o["scores"]["instagram_facebook_potential"]))["title"],
        "approval_items_count": approval_items,
        "external_action_performed": False,
        "money_spent": False,
        "client_contacted": False,
        "publish_status": "draft_only",
        "safety_status": "internal_only",
        "ranked_opportunities": [{"opportunity_id": o["opportunity_id"], "rank": i + 1, "overall_score": o["overall_score"]}
                                 for i, o in enumerate(ranked)],
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", default=True)
    p.add_argument("--cycles", type=int, default=1)
    p.add_argument("--interval-minutes", type=float, default=0)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    cycles_out = []
    cycle_summaries = []
    cycles = max(1, min(args.cycles, 50))
    # Fresh cycle history for this run (write-or-append per cycle).
    CYCLE_HISTORY.parent.mkdir(parents=True, exist_ok=True)
    CYCLE_HISTORY.write_text("")
    for c in range(cycles):
        started_at = nm.now()
        phase_results = []
        for phase_name, scripts in PHASES:
            results = [run_one(s) for s in scripts]
            phase_results.append({"phase": phase_name, "results": results,
                                  "ran_ok": sum(1 for r in results if r["ok"]), "total": len(results)})
        failed = [r for ph in phase_results for r in ph["results"] if not r["ok"]]
        cycles_out.append({"cycle": c + 1, "phases": phase_results, "failed": failed,
                           "ok": len(failed) == 0})
        summ = cycle_summary(c + 1, started_at, phase_results)
        cycle_summaries.append(summ)
        with CYCLE_HISTORY.open("a") as fh:
            fh.write(json.dumps(summ) + "\n")
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

    # End-of-run: build rolling morning agenda + run safety verifier (both dry-run).
    def _run(rel: str) -> dict:
        try:
            proc = subprocess.run([sys.executable, str(ROOT / rel), "--dry-run", "--json"],
                                  capture_output=True, text=True, timeout=120)
            try:
                out = json.loads(proc.stdout)
            except Exception:
                out = {}
            return {"script": rel, "exit_code": proc.returncode, "ok": bool(out.get("ok", proc.returncode == 0)), "data": out}
        except Exception as e:  # noqa: BLE001
            return {"script": rel, "exit_code": -1, "ok": False, "data": {}, "error": str(e)[-200:]}

    rolling = _run("scripts/night_run/build_rolling_morning_money_agenda.py")
    safety = _run("scripts/safety/verify_no_external_execution.py")
    morning_path = "reports/manual_publish/rolling_morning_money_agenda_latest.md"
    top_repeated = next((i["title"] for i in rolling["data"].get("items", []) if i.get("trend_status") in ("repeated", "stable", "rising")), None)
    final_top = (rolling["data"].get("top_5_morning_opportunities") or [None])[0]

    final = {
        "ok": report["ok"] and rolling["ok"] and safety["ok"],
        "title": "All-Night Money Run Summary",
        "generated_at": nm.now(),
        "dry_run": True,
        "cycles_completed": cycles,
        "total_scripts_run": total,
        "failed_scripts": [f["script"] for cy in cycles_out for f in cy["failed"]],
        "top_repeated_opportunity": top_repeated,
        "final_top_opportunity": final_top,
        "safety_verification_status": "passed" if safety["ok"] else "FAILED",
        "morning_agenda_path": morning_path,
        "approval_required": True,
        "external_action_status": "none",
        "cycle_summaries": cycle_summaries,
        "counts": {"cycles": cycles, "total_runs": total, "ran_ok": ran_ok, "failed": len(all_failed)},
        "summary": f"All-night money run complete: {cycles} cycle(s), {ran_ok}/{total} ok. Final top: {final_top}. Safety: {'passed' if safety['ok'] else 'FAILED'}. Draft-only, approval-gated.",
        "safety": {**nm.SAFETY, "scheduler_activated": False, "cron_installed": False, "launchd_installed": False,
                   "systemd_installed": False, "daemon_created": False},
    }
    (ROOT / "reports" / "runtime" / "all_night_money_run_summary_latest.json").write_text(json.dumps(final, indent=2))
    fl = [f"# {final['title']}", "", f"- generated_at: {final['generated_at']}", f"- cycles_completed: {cycles}",
          f"- total_scripts_run: {total}", f"- failed_scripts: {len(final['failed_scripts'])}",
          f"- top_repeated_opportunity: {top_repeated}", f"- final_top_opportunity: {final_top}",
          f"- safety_verification_status: {final['safety_verification_status']}",
          f"- morning_agenda_path: {morning_path}", "- approval_required: true", "- external_action_status: none",
          "- scheduler_activated: false · cron/launchd/systemd/daemon: none"]
    (ROOT / "reports" / "manual_publish" / "all_night_money_run_summary_latest.md").write_text("\n".join(fl) + "\n")

    if args.json:
        print(json.dumps(final, indent=2))
    else:
        print(final["summary"])
        print(f"cycles_completed={cycles} total_scripts_run={total} failed={len(all_failed)} "
              f"final_top={final_top} safety={final['safety_verification_status']} agenda={morning_path} "
              f"approval_required=true external_action=none")
    return 0 if final["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
