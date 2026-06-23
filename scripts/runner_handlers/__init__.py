"""nexus_runner handler registry. ONLY allowlisted job types are dispatched; unknown types
are blocked (never guessed). Telegram and trading jobs are intentionally NOT registered."""
from __future__ import annotations

from . import creative_handlers as C
from . import social_handlers as S
from . import hermes_handlers as H
from . import ops_handlers as O

# job_type -> (handler_fn, risky)
# risky=True means a *real* side effect is possible; the handler still enforces its own gates
# (e.g. social_publish only really publishes with ctx.real_publish + Day 3 adapter gates).
REGISTRY = {
    # creative
    "creative_generate_assets": (C.generate_assets, False),
    "creative_score_assets": (C.score_assets, False),
    "creative_create_approvals": (C.create_approvals, False),
    "creative_create_social_drafts": (C.create_social_drafts, False),
    "creative_revision_request": (C.revision_request, False),
    # social (dry-run safe; real publish gated inside the handler)
    "social_publish": (S.social_publish, True),
    "facebook_publish_dry_run": (S.facebook_publish_dry_run, False),
    # intake / orientation placeholders
    "orient_intake_event": (H.intake_stub, False),
    "niche_research": (H.intake_stub, False),
    "monetization_review": (H.intake_stub, False),
    # ops
    "ops_diagnostic": (O.ops_diagnostic, False),
    "system_status": (O.system_status, False),
    # hermes
    "hermes_command": (H.command_ack, False),
    "command_route_stub": (H.command_ack, False),
    "hermes_model_route_decision": (H.model_route_decision, False),
}


def list_handlers() -> list[dict]:
    return [{"job_type": k, "risky": v[1]} for k, v in sorted(REGISTRY.items())]
