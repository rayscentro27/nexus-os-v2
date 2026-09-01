from nexus_foundation.adaptive_improvement_loop import BUDGET, classify_result, generate_variants, rank_variants, run_adaptive_improvement_loop
from nexus_agent_platform.governed import persistence


def test_no_data_is_not_negative():
    assert classify_result({"sample_status": "NO_REAL_VALIDATION_DATA", "counts": {"VISIT": 0}}) == "NO_DATA"
    assert classify_result({"sample_status": "OBSERVED_SAMPLE_INSUFFICIENT", "counts": {"VISIT": 1}}) == "INSUFFICIENT_EVIDENCE"
    assert classify_result({}, system_failure=True) == "SYSTEM_FAILURE"


def test_variants_are_bounded_and_ranked_deterministically():
    rows = generate_variants({"opportunity_id": "opp_test"}, {"result": "NO_DATA"})
    ranked = rank_variants(rows)
    assert len(rows) == BUDGET["MAX_VALIDATION_VARIANTS"] == 4
    assert ranked[0]["name"] == "individual_vehicle_convenience"
    assert [row["rank"] for row in ranked] == [1, 2, 3, 4]
    assert all(row["cost_usd"] == 0 and row["reversible"] for row in rows)


def test_real_adaptive_run_is_idempotent_and_keeps_no_data(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNED_DATA_DIR", str(tmp_path))
    persistence.append_record("opportunities", {"schema_version": "nexus.business-opportunity.v1", "opportunity_id": "opp_bffe3378956f40bb9317970938eb3f21", "status": "ACCEPT_FOR_VALIDATION"})
    persistence.append_record("business_research", {"type": "GROWTH_VALIDATION_PLAN", "opportunity_id": "opp_bffe3378956f40bb9317970938eb3f21", "result": {"plan_id": "growth_plan_fixture"}})
    persistence.append_record("metrics", {"type": "GROWTH_VALIDATION_METRICS", "opportunity_id": "opp_bffe3378956f40bb9317970938eb3f21", "result": {"sample_status": "NO_REAL_VALIDATION_DATA", "counts": {"VISIT": 0}}})
    first = run_adaptive_improvement_loop()
    second = run_adaptive_improvement_loop()
    assert first["result"] == second["result"] == "NO_DATA"
    assert first["selected"]["variant_id"] == second["selected"]["variant_id"]
    assert len(persistence.read_records("adaptive_variants")) == 4
    assert len(persistence.read_records("adaptive_diagnoses")) == 1
    assert len(persistence.read_records("work_orders")) == 3
    assert second["run"]["external_actions"] is False
