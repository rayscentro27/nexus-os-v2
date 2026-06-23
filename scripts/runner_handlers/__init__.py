"""nexus_runner handler registry. ONLY allowlisted job types are dispatched; unknown types
are blocked (never guessed). Telegram and trading jobs are intentionally NOT registered."""
from __future__ import annotations

from . import creative_handlers as C
from . import social_handlers as S
from . import hermes_handlers as H
from . import ops_handlers as O
from . import intake_handlers as I
from . import design_handlers as D

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
    # intake / orientation (Day 8)
    "transcript_intake_review": (I.transcript_intake_review, False),
    "claim_risk_classify": (I.claim_risk_classify, False),
    "service_opportunity_extract": (I.service_opportunity_extract, False),
    # creative design department (Day 9)
    "creative_create_design_brief": (D.create_design_brief, False),
    "creative_generate_design_variants": (D.generate_design_variants, False),
    "creative_score_design_variants": (D.score_design_variants, False),
    "creative_compare_design_variants": (D.compare_design_variants, False),
    "design_register_inspiration": (D.register_inspiration, False),
    "design_extract_patterns": (D.extract_patterns, False),
    "design_create_feature_packet": (D.create_feature_packet, False),
    "design_review_ui_quality": (D.review_ui_quality, False),
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
