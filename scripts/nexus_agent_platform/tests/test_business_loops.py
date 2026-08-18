from nexus_agent_platform.loops.business import (
    OPEN_SOURCE_SCOUT_LOOP,
    SEO_OPPORTUNITY_LOOP,
    REVENUE_OPPORTUNITY_LOOP,
    RESEARCH_INTAKE_LOOP,
    eligibility_matrix,
)
from nexus_agent_platform.loops.runtime import LoopRuntime, LoopStateStore


def test_selected_business_loops_have_verifiers_and_zero_ai_policy():
    for spec in (OPEN_SOURCE_SCOUT_LOOP, SEO_OPPORTUNITY_LOOP, REVENUE_OPPORTUNITY_LOOP, RESEARCH_INTAKE_LOOP):
        assert spec.max_ai_calls == 0
        assert spec.model_tier == "T0_DETERMINISTIC"
        assert spec.verifier_name
        assert spec.dedupe_key
        assert spec.state_key
        assert spec.approval_boundary


def test_business_loop_second_identical_run_is_no_change(monkeypatch, tmp_path):
    monkeypatch.setenv("NEXUS_EXECUTION_TELEMETRY_PATH", str(tmp_path / "telemetry.jsonl"))
    runtime = LoopRuntime(LoopStateStore(tmp_path / "state.json"), tmp_path / "ledger.jsonl")
    records = [{"id": "crawl4ai", "repository": "unclecode/crawl4ai", "title": "Crawl4AI", "source_url": "https://github.com/unclecode/crawl4ai", "provenance": "public_fixture", "evidence_classification": "KNOWN"}]
    first = runtime.run(OPEN_SOURCE_SCOUT_LOOP, {"records": records, "proof": "business-test"})
    second = runtime.run(OPEN_SOURCE_SCOUT_LOOP, {"records": records, "proof": "business-test"})
    assert first.verifier["status"] == "pass"
    assert first.ledger_record["delta_status"] == "CHANGED"
    assert second.ledger_record["delta_status"] == "NO_CHANGE"
    assert second.ai_calls == 0
    assert second.input_tokens == 0
    assert second.output_tokens == 0
    assert second.estimated_cost == 0.0


def test_only_four_business_loops_are_qualified():
    matrix = {row["loop_id"]: row["classification"] for row in eligibility_matrix()}
    assert matrix["open_source_scout_loop"] == "QUALIFIED"
    assert matrix["seo_opportunity_loop"] == "QUALIFIED"
    assert matrix["revenue_opportunity_loop"] == "QUALIFIED_WITH_LIMITS"
    assert matrix["research_intake_loop"] == "QUALIFIED"
    assert matrix["affiliate_opportunity_loop"] == "DEFER"
    assert matrix["grant_opportunity_loop"] == "DEFER"
