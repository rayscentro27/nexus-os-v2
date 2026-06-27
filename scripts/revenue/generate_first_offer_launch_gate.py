#!/usr/bin/env python3
"""First Offer Launch Gate — $97 Readiness Review go/no-go (report-only, never launches)."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "partners"))
import launch_model as lm  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(); p.add_argument("--dry-run", action="store_true", default=True); p.add_argument("--json", action="store_true"); a = p.parse_args()
    gate = lm.readiness_review_launch_gate()
    r = {
        "ok": True, "title": "First Offer Launch Gate", "generated_at": lm.now(), "dry_run": True,
        "gate": gate, "can_launch": gate["can_launch"],
        "counts": {"satisfied": len(gate["satisfied"]), "blockers": len(gate["blockers"])},
        "summary": f"$97 Readiness Review launch gate: can_launch={gate['can_launch']}. "
                   f"{len(gate['blockers'])} blocker(s). No launch, publish, or charge occurred.",
        "safety": {**lm.SAFETY, "offer_launched": False, "offer_published": False, "client_charged": False,
                   "payment_link_activated": False},
    }
    md = ["## $97 Readiness Review launch gate", f"- can_launch: {gate['can_launch']}",
          f"- payment_status: {gate['payment_status']}", "", "## Satisfied"] + [f"- {x}" for x in gate["satisfied"]]
    md += ["", "## Blockers"] + [f"- {x}" for x in gate["blockers"]]
    md += ["", f"## Next action", f"- {gate['recommended_next_action']}"]
    lm.write_report("first_offer_launch_gate_latest", r, md)
    print(json.dumps(r, indent=2) if a.json else r["summary"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
