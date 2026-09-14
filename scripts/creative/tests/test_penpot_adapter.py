from scripts.creative.penpot_adapter import PenpotAdapter, PenpotRuntime, PenpotUnavailable


def test_unconfigured_penpot_is_external_gated_and_does_not_claim_artifact():
    adapter = PenpotAdapter(PenpotRuntime(None, "configured_api_gateway", False))
    status = adapter.status()
    assert status["runtime_started"] is False
    assert status["health"] == "EXTERNAL_GATED"
    try:
        adapter.create_editable_artifact({"design_project_id": "admin"})
    except PenpotUnavailable as exc:
        assert str(exc) == "penpot_runtime_not_connected"
    else:
        raise AssertionError("unconfigured Penpot must not claim an artifact")


def test_connected_runtime_exposes_only_capability_contract():
    adapter = PenpotAdapter(PenpotRuntime("http://private-penpot", "official_mcp_plugin", True))
    status = adapter.status()
    assert status["health"] == "PASS_REAL"
    assert status["mcp_available"] is True
    assert "create_frame" in status["operations"]
