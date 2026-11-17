from nova.approved_mcp_registry import _classify


def test_volatile_read_description_is_catalogued_as_read_only():
    result = _classify({
        "server_id": "nexus_mcp_remote",
        "name": "nexus_get_durable_jobs",
        "description": "VOLATILE read of current production durable-job records. Never creates or changes work.",
        "annotations": {},
        "input_schema": {"type": "object"},
    }, {
        "server_id": "nexus_mcp_remote",
        "cost_class": "ZERO",
        "external_effect": True,
        "production_effect": True,
        "reversible": False,
    })
    assert result["read_write_class"] == "READ"
    assert result["metadata_complete"] is True
    assert result["write_allowed"] is False
