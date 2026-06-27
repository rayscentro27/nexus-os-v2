#!/usr/bin/env python3
"""Phase 4 — Rolling morning money agenda.

Combines money opportunities across overnight cycles into one prioritized, de-duplicated agenda with
trend tracking. Reads the cycle history JSONL (if present) and the money model. Report-only.

    python3 scripts/night_run/build_rolling_morning_money_agenda.py --dry-run --json --lookback-hours 12 --max-items 25
"""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "scripts" / "research"))
from night_run_model import write_report, now, SAFETY  # noqa: E402
import money_opportunity_model as mo  # noqa: E402

CYCLE_HISTORY = ROOT / "reports" / "runtime" / "overnight_money_cycle_history_latest.jsonl"


def parse_ts(s: str):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def load_cycles(lookback_hours: float) -> list[dict]:
    """Each cycle: {cycle_number, started_at, ranked_opportunities:[{opportunity_id, rank, overall_score}]}."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    cycles: list[dict] = []
    if CYCLE_HISTORY.exists():
        for line in CYCLE_HISTORY.read_text(errors="ignore").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                c = json.loads(line)
            except Exception:
                continue
            ts = parse_ts(c.get("started_at", "")) or datetime.now(timezone.utc)
            if ts >= cutoff and isinstance(c.get("ranked_opportunities"), list):
                cycles.append(c)
    if not cycles:
        # Fallback: synthesize one cycle from the deterministic model.
        ranked = mo.ranked()
        cycles = [{"cycle_number": 1, "started_at": now(),
                   "ranked_opportunities": [{"opportunity_id": o["opportunity_id"], "rank": i + 1,
                                             "overall_score": o["overall_score"]} for i, o in enumerate(ranked)]}]
    cycles.sort(key=lambda c: c.get("cycle_number", 0))
    return cycles


def trend_for(times_seen: int, total_cycles: int, rank_change: int, in_latest: bool, is_review: bool) -> str:
    if is_review:
        return "needs_ray_review"
    if not in_latest:
        return "falling"  # was seen earlier but not in the latest cycle
    if times_seen == 1 and total_cycles > 1:
        return "new"
    if rank_change > 0:
        return "rising"
    if rank_change < 0:
        return "falling"
    if times_seen == total_cycles and total_cycles > 1:
        return "repeated"
    return "stable"


def build(max_items: int, lookback_hours: float) -> dict:
    cycles = load_cycles(lookback_hours)
    total_cycles = len(cycles)
    latest_cycle_num = cycles[-1]["cycle_number"] if cycles else 1
    model = {o["opportunity_id"]: o for o in mo.ranked()}

    seen: dict[str, dict] = {}
    for c in cycles:
        cnum = c["cycle_number"]
        for entry in c["ranked_opportunities"]:
            oid = entry["opportunity_id"]
            rec = seen.setdefault(oid, {"first_cycle": cnum, "first_rank": entry["rank"], "times": 0,
                                        "last_cycle": cnum, "last_rank": entry["rank"]})
            rec["times"] += 1
            rec["last_cycle"] = cnum
            rec["last_rank"] = entry["rank"]

    items = []
    for oid, rec in seen.items():
        m = model.get(oid)
        if not m:
            continue
        s = m["scores"]
        rank_change = rec["first_rank"] - rec["last_rank"]  # positive = improved
        in_latest = rec["last_cycle"] == latest_cycle_num
        is_review = "ray_review_approval_item" in m["opportunity_types"]
        items.append({
            "opportunity_id": oid, "title": m["title"],
            "opportunity_type": m["opportunity_types"][0],
            "opportunity_types": m["opportunity_types"],
            "overall_score": m["overall_score"],
            "revenue_potential": s["revenue_potential"], "speed_to_launch": s["speed_to_launch"],
            "risk_level": s["risk_level"], "client_value": s["client_value"],
            "affiliate_potential": s["affiliate_potential"], "subscription_potential": s["subscription_potential"],
            "funding_commission_potential": s["funding_commission_potential"],
            "content_potential": s["content_potential"], "landing_page_potential": s["landing_page_potential"],
            "social_video_potential": max(s["tiktok_potential"], s["instagram_facebook_potential"]),
            "hermes_discussion_value": s["hermes_discussion_value"],
            "first_seen_cycle": rec["first_cycle"], "last_seen_cycle": rec["last_cycle"],
            "times_seen": rec["times"],
            "trend_status": trend_for(rec["times"], total_cycles, rank_change, in_latest, is_review),
            "rank_change": rank_change,
            "recommended_action": m["ray_next_action"],
            "approval_required": True, "publish_status": "draft_only", "external_action_performed": False,
        })
    items.sort(key=lambda x: x["overall_score"], reverse=True)
    items = items[:max_items]

    def top(key, n=3, pred=None):
        pool = [i for i in items if (pred(i) if pred else True)]
        pool.sort(key=lambda x: x.get(key, 0), reverse=True)
        return [i["title"] for i in pool[:n]]

    def has_type(t):
        return lambda i: t in i["opportunity_types"]

    return {
        "ok": True, "title": "Rolling Morning Money Agenda", "generated_at": now(), "dry_run": True,
        "publish_status": "draft_only", "approval_required": True,
        "cycles_considered": total_cycles, "lookback_hours": lookback_hours,
        "items": items,
        "top_5_morning_opportunities": [i["title"] for i in items[:5]],
        "top_3_fastest_money": top("speed_to_launch"),
        "top_3_lowest_risk": [i["title"] for i in sorted(items, key=lambda x: x["risk_level"])[:3]],
        "top_3_affiliate": top("affiliate_potential", pred=has_type("affiliate_opportunity")),
        "top_3_subscription": top("subscription_potential", pred=has_type("monthly_subscription")),
        "top_3_funding_commission": top("funding_commission_potential"),
        "top_3_landing_page": top("landing_page_potential", pred=has_type("landing_page_opportunity")),
        "top_3_social_video": top("social_video_potential", pred=has_type("content_opportunity")),
        "top_3_workflow": top("client_value", pred=has_type("client_workflow_improvement")),
        "top_3_ray_approval": top("overall_score", pred=has_type("ray_review_approval_item")),
        "top_3_hermes_topics": top("hermes_discussion_value", pred=has_type("hermes_discussion_topic")),
        "top_3_not_to_do_yet": [
            "Publish/post/upload/deploy anything.",
            "Charge clients / activate payment links / connect billing.",
            "Activate scheduler/connectors or contact clients/partners.",
        ],
        "counts": {"items": len(items), "cycles": total_cycles},
        "summary": f"Rolling agenda from {total_cycles} cycle(s): top opportunity '{items[0]['title'] if items else 'n/a'}'. Draft-only.",
        "safety": {**SAFETY, "external_action_performed": False},
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", default=True)
    p.add_argument("--json", action="store_true")
    p.add_argument("--max-items", type=int, default=25)
    p.add_argument("--lookback-hours", type=float, default=12)
    a = p.parse_args()
    r = build(max(1, a.max_items), max(0.1, a.lookback_hours))
    md = [f"- cycles considered: {r['cycles_considered']} · lookback {r['lookback_hours']}h", "", "## Top 5 morning opportunities"]
    md += [f"- {x}" for x in r["top_5_morning_opportunities"]]
    for label, key in [("Top 3 fastest money", "top_3_fastest_money"), ("Top 3 lowest risk", "top_3_lowest_risk"),
                       ("Top 3 affiliate", "top_3_affiliate"), ("Top 3 subscription", "top_3_subscription"),
                       ("Top 3 funding commission", "top_3_funding_commission"), ("Top 3 landing page", "top_3_landing_page"),
                       ("Top 3 social video", "top_3_social_video"), ("Top 3 workflow", "top_3_workflow"),
                       ("Top 3 Ray approval", "top_3_ray_approval"), ("Top 3 Hermes topics", "top_3_hermes_topics"),
                       ("Top 3 not to do yet", "top_3_not_to_do_yet")]:
        md += ["", f"## {label}"] + [f"- {x}" for x in r[key]]
    md += ["", "## Items (with trend)"]
    for i in r["items"]:
        md.append(f"- [{i['overall_score']}] {i['title']} · {i['trend_status']} · seen {i['times_seen']}x (c{i['first_seen_cycle']}->c{i['last_seen_cycle']}) · Δrank {i['rank_change']}")
    write_report("rolling_morning_money_agenda_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
