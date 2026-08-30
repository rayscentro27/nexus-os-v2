import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from nexus_agent_platform.evidence_broker import project_evidence, evidence_summary
from nexus_agent_platform.claim_validator import validate_response
from nexus_agent_platform.state import AgentState


def test_evidence_projection_is_scoped_and_provenanced():
    payload = project_evidence(
        "What is running?",
        "get_system_status",
        {"status": "ok", "data": {"hermes": "RUNNING", "token": "never include"},
         "provenance": {"source": "runtime", "freshness": "live"}},
    )
    assert payload["authority"] == "TRUTHKERNEL"
    assert len(payload["evidence"]) == 1
    assert payload["evidence"][0]["type"] == "FACT"
    assert "token" not in payload["evidence"][0]["claim"]
    assert evidence_summary(payload)["FACT"] == 1


def test_failed_read_becomes_unknown_not_fact():
    payload = project_evidence("What is healthy?", "get_system_status", {
        "status": "unavailable", "error": "source unavailable", "provenance": {"source": "runtime"}
    })
    assert payload["evidence"] == []
    assert payload["unknowns"][0]["type"] == "UNKNOWN"
    assert payload["allowed_capabilities"] == []


def test_claim_validator_rejects_healthy_when_status_unknown():
    payload = project_evidence("What is healthy?", "get_system_status", {
        "status": "unavailable", "error": "health source unavailable", "provenance": {"source": "runtime"}
    })
    result = validate_response("Everything is healthy and running.", payload)
    assert result["valid"] is False
    assert "unsupported_claim_over_unknown_evidence" in result["violations"]


def test_claim_validator_rejects_guaranteed_revenue():
    result = validate_response("This guarantees revenue.", {"evidence": [], "unknowns": []})
    assert result["valid"] is False
    assert "guaranteed_revenue_claim" in result["violations"]


def test_agent_state_round_trips_evidence_contract():
    state = AgentState(evidence_payload={"evidence": []}, claim_validation={"valid": True})
    restored = AgentState.from_dict(state.to_dict())
    assert restored.evidence_payload == {"evidence": []}
    assert restored.claim_validation == {"valid": True}
