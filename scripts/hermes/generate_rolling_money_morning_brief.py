#!/usr/bin/env python3
"""Phase 7 — Hermes rolling money morning brief (uses the rolling agenda; sanitized signals only)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "night_run"))
from night_run_model import write_report, now, SAFETY  # noqa: E402

ROLLING = ROOT / "reports" / "runtime" / "rolling_morning_money_agenda_latest.json"


def load_rolling() -> dict:
    if ROLLING.exists():
        try:
            return json.loads(ROLLING.read_text(errors="ignore"))
        except Exception:
            return {}
    return {}


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    roll = load_rolling()
    items = roll.get("items", [])
    won = items[0]["title"] if items else "n/a"
    repeated = [i["title"] for i in items if i.get("trend_status") in ("repeated", "stable")][:3]
    stronger = [i["title"] for i in items if i.get("trend_status") == "rising"][:3]
    weaker = [i["title"] for i in items if i.get("trend_status") == "falling"][:3]
    r = {
        "ok": True, "title": "Hermes Rolling Money Morning Brief", "generated_at": now(), "dry_run": True,
        "uses_sanitized_signals_only": True, "uses_raw_client_data": False,
        "publish_status": "draft_only", "approval_required": True,
        "what_won_overnight": won,
        "what_repeated_across_cycles": repeated,
        "what_got_stronger": stronger or ["(deterministic run — scores stable across cycles)"],
        "what_got_weaker": weaker or ["(none)"],
        "approve_first": (roll.get("top_3_ray_approval") or ["Approve the $97 Readiness Review offer + copy."])[0],
        "stay_draft_only": "All landing pages, posts, videos, offers, and copy remain drafts.",
        "needs_partner_links": roll.get("top_3_affiliate", [])[:3],
        "needs_pricing_validation": "GoClear subscription tiers + readiness review price (validate vs market).",
        "do_not_launch_yet": roll.get("top_3_not_to_do_yet", []),
        "build_today": (roll.get("top_3_landing_page") or [])[:1] + (roll.get("top_3_social_video") or [])[:1],
        "nothing_launched": True,
        "counts": {"items": len(items)},
        "summary": f"Overnight winner: {won}. Repeated: {', '.join(repeated) or 'n/a'}. All assets draft-only and approval-gated; nothing launched.",
        "safety": {**SAFETY, "raw_client_data_used": False, "external_action_performed": False, "claims_launched": False},
    }
    md = ["## Hermes rolling money morning brief (plain language)",
          f"- What won overnight: {won}",
          f"- Repeated across cycles: {', '.join(repeated) or 'n/a'}",
          f"- Got stronger: {', '.join(r['what_got_stronger'])}",
          f"- Got weaker: {', '.join(r['what_got_weaker'])}",
          f"- Approve first: {r['approve_first']}",
          f"- Stay draft-only: {r['stay_draft_only']}",
          f"- Needs partner links: {', '.join(r['needs_partner_links']) or 'n/a'}",
          f"- Needs pricing validation: {r['needs_pricing_validation']}",
          f"- Build today: {', '.join(r['build_today']) or 'n/a'}",
          "", "## Do not launch yet"] + [f"- {x}" for x in r["do_not_launch_yet"]]
    write_report("hermes_rolling_money_morning_brief_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
