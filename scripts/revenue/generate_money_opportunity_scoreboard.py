#!/usr/bin/env python3
"""Money opportunity scoreboard (ranked, report-only)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "research"))
import money_opportunity_model as mo  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    items = mo.ranked()
    board = [{
        "rank": i + 1, "opportunity_id": o["opportunity_id"], "title": o["title"],
        "overall_score": o["overall_score"], "types": o["opportunity_types"],
        "revenue_potential": o["scores"]["revenue_potential"], "speed_to_launch": o["scores"]["speed_to_launch"],
        "risk_level": o["scores"]["risk_level"], "affiliate_potential": o["scores"]["affiliate_potential"],
        "subscription_potential": o["scores"]["subscription_potential"],
        "funding_commission_potential": o["scores"]["funding_commission_potential"],
        "approval_needed": o["approval_needed"], "ray_next_action": o["ray_next_action"],
    } for i, o in enumerate(items)]
    r = {
        "ok": True, "title": "Money Opportunity Scoreboard", "generated_at": mo.now(), "dry_run": True,
        "publish_status": "draft_only", "approval_required": True,
        "scoreboard": board,
        "fastest_to_launch": mo.fastest_to_launch()["title"],
        "lowest_risk": mo.lowest_risk()["title"],
        "best_overall": mo.best_overall()["title"],
        "counts": {"opportunities": len(board)},
        "summary": f"Top opportunity: {board[0]['title']} ({board[0]['overall_score']}). Fastest: {mo.fastest_to_launch()['title']}. Lowest risk: {mo.lowest_risk()['title']}.",
        "safety": {**mo.SAFETY, "external_action_performed": False},
    }
    md = [f"- best overall: {r['best_overall']}", f"- fastest to launch: {r['fastest_to_launch']}", f"- lowest risk: {r['lowest_risk']}", "", "## Scoreboard"]
    for b in board:
        md.append(f"{b['rank']}. [{b['overall_score']}] {b['title']} · rev {b['revenue_potential']} · speed {b['speed_to_launch']} · risk {b['risk_level']}")
    mo.write_report("money_opportunity_scoreboard_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
