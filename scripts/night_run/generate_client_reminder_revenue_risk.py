#!/usr/bin/env python3
"""Part 13 — Reminders / stuck-client revenue risk (internal/report-only)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "scripts" / "client_workflow"))
import night_run_model as nm  # noqa: E402
import client_workflow_model as cw  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    clients, source = cw.load_clients()
    stuck = []
    for c in clients:
        ds = c["days_stuck"]
        if ds >= cw.REMINDER_TIMINGS["incomplete_setup_days"]:
            stuck.append({
                "client_id": c["client_id"], "client_label": c["client_label"], "current_stage": c["current_stage"],
                "days_stuck": ds, "revenue_risk_level": cw.revenue_risk(ds), "escalation_status": cw.escalation(ds),
                "reminder_draft": f"Reminder (draft, internal): {c['client_label']} — complete the next step at '{c['current_stage']}'.",
                "external_send": False,
            })
    stuck.sort(key=lambda x: x["days_stuck"], reverse=True)
    high_risk = [s for s in stuck if s["revenue_risk_level"] in ("high", "critical")]
    r = {
        "ok": True, "title": "Client Reminder + Revenue Risk", "generated_at": nm.now(), "dry_run": True,
        "data_source": source, "timings_days": cw.REMINDER_TIMINGS,
        "stuck_clients": stuck, "revenue_risk_clients": high_risk,
        "next_actions": [f"{s['client_label']}: follow up at '{s['current_stage']}' ({s['days_stuck']}d stuck)" for s in stuck[:5]],
        "counts": {"total_clients": len(clients), "stuck": len(stuck), "revenue_risk": len(high_risk),
                   "reminder_drafts": len(stuck), "external_messages_sent": 0},
        "summary": f"{len(stuck)} stuck client(s), {len(high_risk)} at revenue risk; {len(stuck)} reminder draft(s) generated. No external reminder sent (consent/approval required).",
        "safety": {**nm.SAFETY, "external_reminder_sent": False},
    }
    md = ["## Stuck clients"]
    for s in stuck:
        md.append(f"- {s['client_label']} · {s['current_stage']} · {s['days_stuck']}d · risk={s['revenue_risk_level']} · escalate={s['escalation_status']}")
    md += ["", "## Next actions"] + [f"- {x}" for x in r["next_actions"]]
    nm.write_report("client_reminder_revenue_risk_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
