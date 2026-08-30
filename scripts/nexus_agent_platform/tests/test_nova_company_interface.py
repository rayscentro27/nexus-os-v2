import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nexus_agent_platform.nova_company_context import context_for_prompt
from nexus_agent_platform.nexus_command_acknowledgement import acknowledge_command


def test_company_context_prompt_is_bounded_and_non_authoritative():
    rendered = context_for_prompt({
        "current_status": {"program_state": "ACTIVE"},
        "operations": {"status": "UNKNOWN"},
        "research": {}, "ray_attention": {}, "business": {"top_priority": {}},
        "blockers": [], "unknown": ["freshness unavailable"],
        "authority": "CONTEXT_ONLY_TRUTHKERNEL_REVALIDATES",
    })
    assert "CONTEXT_ONLY_TRUTHKERNEL_REVALIDATES" in rendered
    assert "ACTIVE" in rendered


def test_command_acknowledgement_does_not_overclaim_completion():
    ack = acknowledge_command(
        "req-1", authority_status="AUTHORIZED_READ_ONLY",
        current_state="QUEUED", status="QUEUED",
        work_order_id="wo-1", assigned_department="OPERATIONS",
    )
    assert ack["command_received"] is True
    assert ack["status"] == "QUEUED"
    assert ack["current_state"] != "COMPLETED"
    assert ack["authority"] == "NEXUS_TRUTHKERNEL"


def test_acknowledgement_rejects_unknown_state():
    try:
        acknowledge_command("req-1", authority_status="UNKNOWN", current_state="UNKNOWN", status="MAGIC")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown acknowledgement state accepted")
