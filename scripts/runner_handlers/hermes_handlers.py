"""Hermes / intake placeholder handlers. These NEVER pretend live AI work happened."""
from __future__ import annotations

from ._base import ok

ACK = ("Command acknowledged. No live model route executed. "
       "Next action should be reviewed or routed by Ray.")


def command_ack(job, ctx) -> dict:
    return ok({"note": ACK, "command": (job.get("input") or {}).get("command")})


def intake_stub(job, ctx) -> dict:
    return ok({"note": "Intake/orientation acknowledged. No external research/model call performed.",
               "job_type": job.get("job_type")})
