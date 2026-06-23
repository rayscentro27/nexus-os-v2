"""Social job handlers — Facebook publish via the Day 3 adapter. DRY-RUN by default.

A real publish requires ctx['real_publish'] True AND all Day 3 adapter gates (approval=
approved, account=Clear Credentials, env token present, publish_enabled=true). The adapter
never publishes Instagram, never sends Telegram, never trades.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "social"))
import facebook_publisher  # noqa: E402
from ._base import ok, fail, blocked


def _publish(job, ctx, force_dry: bool) -> dict:
    post_id = (job.get("input") or {}).get("post_id")
    if not post_id:
        return blocked("no post_id in job input")
    real = bool(ctx.get("real_publish")) and not force_dry
    result = facebook_publisher.publish(post_id, real_publish=real)
    if result.get("ok") and (result.get("mode") == "dry_run" or result.get("published")):
        return ok({"mode": result.get("mode"), **{k: v for k, v in result.items() if k != "ok"}})
    return fail(result.get("blocker") or str(result.get("error") or "publish not completed"), result)


def social_publish(job, ctx) -> dict:
    return _publish(job, ctx, force_dry=False)


def facebook_publish_dry_run(job, ctx) -> dict:
    return _publish(job, ctx, force_dry=True)
