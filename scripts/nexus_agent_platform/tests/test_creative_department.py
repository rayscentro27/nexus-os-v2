from pathlib import Path

from nexus_agent_platform.creative.department import build_brief, genericness_gate, run_real_creative_e2e, territories


def test_territories_pass_distinctiveness_gate():
    brief = build_brief()
    rows = territories(brief)
    result = genericness_gate(rows)
    assert len(rows) == 4
    assert result["status"] == "PASS"
    assert result["distinct_hook_families"] == 4


def test_real_department_e2e_is_repeatable_and_safe(tmp_path, monkeypatch):
    monkeypatch.setattr("nexus_agent_platform.creative.department.ARTIFACT_ROOT", Path(tmp_path))
    first = run_real_creative_e2e()
    second = run_real_creative_e2e()
    assert first["status"] == second["status"] == "PASS"
    assert first["genericness_gate"]["status"] == "PASS"
    assert first["receipt"]["receipt_id"] == second["receipt"]["receipt_id"]
    assert first["work_order"]["work_order_id"] == second["work_order"]["work_order_id"]
    assert first["external_actions"] is False
    assert Path(first["video"]["artifact_path"]).exists()
    assert all(Path(item).exists() for item in (first["landing"]["v2"]["desktop"], first["landing"]["v2"]["mobile"]))
