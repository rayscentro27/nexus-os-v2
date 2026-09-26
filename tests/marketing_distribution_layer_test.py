import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from nexus_agent_platform.marketing_distribution import (  # noqa: E402
    attribution_schema, channel_adaptation, email_capability_schema,
    email_permission_matrix, nurture_sequences, retry_policy,
    social_capability_schema, social_permission_matrix,
)


def test_social_contracts_are_complete_and_governed():
    schema = social_capability_schema()
    assert set(schema["capability_ids"]) == {f"marketing.social.{x}" for x in ("facebook", "instagram", "linkedin", "youtube", "tiktok", "x")}
    assert social_permission_matrix()["PUBLISH"] == "EXISTING_NEXUS_POLICY"
    assert social_permission_matrix()["AD_SPEND"] == "APPROVAL_REQUIRED"


def test_channel_adaptation_is_not_identical_copy_fanout():
    rows = [channel_adaptation(c, "A" * 200, "Same base caption") for c in ("facebook", "instagram", "linkedin", "youtube", "tiktok", "x")]
    assert len({row["cta"] for row in rows}) >= 4
    assert len({row["asset"] for row in rows}) >= 4
    assert all(len(row["hook"]) <= row["hook_max"] for row in rows)


def test_email_governance_and_tracking_fail_closed():
    assert email_permission_matrix()["BULK_EMAIL"] == "BLOCKED_FOR_THIS_MISSION"
    assert email_capability_schema()["delivery_not_inferred_from_acceptance"] is True
    assert attribution_schema()["conversion_claim_requires_event"] is True


def test_nurture_and_retry_contracts_are_draft_safe():
    sequences = nurture_sequences("funnel")
    assert len(sequences) == 6
    assert all(item["status"] == "DRAFT_NOT_SENT" for item in sequences)
    assert retry_policy()["auth_failure"] == "HOLD_AND_ESCALATE"
    assert "duplicate_send_without_idempotency" in retry_policy()["never"]
