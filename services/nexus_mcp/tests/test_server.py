from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.nexus_mcp import server


def test_tool_surface_is_read_only_and_complete():
    names = {tool.name for tool in server.mcp._tool_manager.list_tools()}
    assert names == set(server.TOOL_NAMES)
    assert all(name.startswith("nexus_get_") for name in names)


def test_public_result_preserves_canonical_state_and_metadata():
    value = server._public_result(
        "nexus_get_blockers",
        {
            "status": "success",
            "source": "governed_state",
            "source_type": "live_governed_state",
            "freshness": "live",
            "data": {"blockers": [{"id": "b-1", "status": "BLOCKED"}]},
            "provenance": {"source_timestamp": "2026-08-31T00:00:00+00:00"},
        },
    )
    assert value["status"] == "ok"
    assert value["items"] == [{"id": "b-1", "status": "BLOCKED"}]
    assert value["metadata"] == {
        "read_only": True,
        "canonical": True,
        "freshness": "live",
        "item_count": 1,
        "source_commit": None,
        "currentness": "CURRENT",
        "live_response_eligible": True,
        "filtered_historical_count": 0,
        "filtered_synthetic_count": 0,
        "filtered_other_noncurrent_count": 0,
    }


def test_public_result_marks_partial_business_state_and_live_health():
    business = server._public_result(
        "nexus_get_business_state",
        {"status": "partial", "freshness": "live", "data": {}, "provenance": {}},
    )
    health = server._public_result(
        "nexus_get_system_health",
        {"status": "partial", "freshness": "live", "data": {}, "provenance": {}},
    )
    assert business["metadata"]["currentness"] == "PARTIAL"
    assert health["metadata"]["currentness"] == "CURRENT"


def test_canonical_read_failure_is_explicit_and_not_fabricated(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(server, "RECEIPT_DIR", tmp_path)
    monkeypatch.setattr(server, "read_canonical", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("offline")))
    value = server._call("nexus_get_reviews")
    assert value["status"] == "NOT_AVAILABLE"
    assert value["items"] == []
    receipts = list(tmp_path.glob("*.json"))
    assert len(receipts) == 1
    receipt = json.loads(receipts[0].read_text())
    assert receipt["result_status"] == "NOT_AVAILABLE"
    assert receipt["read_only"] is True
    assert receipt["authority_owner"] == "Nexus"


@pytest.mark.parametrize("name", server.TOOL_NAMES)
def test_each_tool_has_empty_object_input_schema(name):
    tool = next(tool for tool in server.mcp._tool_manager.list_tools() if tool.name == name)
    assert tool.parameters == {} or tool.parameters.get("properties", {}) == {}
