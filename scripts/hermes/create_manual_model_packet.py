#!/usr/bin/env python3
"""Nexus OS v2 — manual model prompt-packet generator.

When Hermes cannot safely call a model directly, it produces a clean, paste-ready packet for
Ray to run in Claude Code / OpenCode / Codex. Supports the workflow: Hermes architects → Ray's
manual tool executes. Writes the packet to /tmp + a nexus_events row. No model call, no secrets.

    python3 scripts/hermes/create_manual_model_packet.py --task "Implement a safe transcript intake review system"
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "social"))
from _supabase import configured, event  # noqa: E402

OUT = Path("/tmp/nexus_manual_model_packet.md")


def build_packet(task: str, context: str = "") -> str:
    return f"""# Nexus OS v2 — Manual Model Packet
Generated: {datetime.now(timezone.utc).isoformat()}

## Task
{task}

## Safe context summary
{context or "(Nexus OS v2: Supabase-first; ledger = nexus_events; jobs = agent_jobs; approvals "
            "gate risky actions; nexus_runner executes only allowlisted handlers.)"}

## Exact requested output
- A concrete, minimal, additive implementation plan and/or code.
- Keep changes small and buildable; preserve existing behavior.

## Boundaries (must follow)
- Do NOT print or commit secrets; do NOT commit .env.
- Do NOT add public/anon Supabase policies; do NOT weaken RLS.
- Do NOT enable Telegram sends, real social publish, live/funded trading, or schedulers.
- Do NOT call paid/external model APIs by default.
- Frontend uses only VITE_SUPABASE_URL + VITE_SUPABASE_ANON_KEY; service role is server-side only.

## Prohibited actions
- No deploy/push unless Ray explicitly approves.
- No arbitrary shell from agents; no autonomous loops/daemons.

## Verification commands
```
npm run build
python3 scripts/nexus_runner.py --once --limit 1 --dry-run
```

## Reminders
- Do not print secrets in output.
- Do not deploy or push unless approved.
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--context", default="")
    args = ap.parse_args()

    packet = build_packet(args.task, args.context)
    OUT.write_text(packet)
    if configured():
        event("communication", "hermes_manual_packet_created", "success",
              "Manual model packet created", f"task: {args.task[:120]}")
    print(f"Manual model packet written → {OUT} (no model call, no secrets).")
    print("\n".join(packet.splitlines()[:6]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
