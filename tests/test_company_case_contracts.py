import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from research.company_case_contracts import completion_gaps, decision_packet
from research import research_case_engine


def test_trading_case_requires_evidence_beyond_a_single_backtest():
    case = {"objective_family": "TRADING_INTELLIGENCE", "objective": "Test strategy",
            "success_criteria": ["robust evidence"], "final_recommendation": "GET_MORE_EVIDENCE",
            "explicit_deterministic_rules": {"entry": "close above range"},
            "source_supported_rules": ["source id"], "nexus_assumptions": ["cost model"],
            "no_lookahead_assessment": "not done", "markets": ["EURUSD"], "timeframes": ["H1"],
            "risk_model": {"risk": 0.01}, "backtest_results": {"trades": 16}}
    gaps = completion_gaps(case)
    assert "robustness_results" in gaps
    assert "failure_regimes" in gaps
    assert "profit_factor" in gaps
    assert "success_criteria_not_satisfied" in gaps


def test_decision_packet_preserves_gaps_and_ray_choices_are_external():
    case = {"case_id": "c1", "objective_family": "BUSINESS_OPPORTUNITIES",
            "objective": "Test opportunity", "success_criteria": ["validate demand"],
            "recommendations": [{"recommendation": "TEST", "recommendation_reason": "cheap test", "confidence": .4}]}
    packet = decision_packet(case)
    assert packet["ray_decision_status"] == "NOT_READY"
    assert "financial_analysis" in packet
    assert "APPROVE" not in packet["nexus_recommendation"]
    assert "expected_cost" in packet


def test_department_completion_never_completes_parent_case(monkeypatch):
    original = {"case_id": "c1", "status": "DEPARTMENT_DEVELOPMENT", "department_requests": [],
                "next_research_action": "CONTINUE_CASE", "case_schema_version": "nexus.research-case.v1"}
    captured = {}
    monkeypatch.setattr(research_case_engine, "get_case", lambda _: original)
    monkeypatch.setattr(research_case_engine, "_save", lambda _case, _event, **details: captured.update(details) or details)
    result = research_case_engine.record_department_response(case_id="c1", department="SYSTEMS", status="COMPLETED")
    assert result["ok"] is True
    assert captured["status"] == "DEPARTMENT_DEVELOPMENT"
    assert captured["continue_research"] is True
    assert captured["next_action"] == "EVALUATE_CASE_COMPLETION_CONTRACT"


def test_company_case_projection_contains_required_shared_fields(monkeypatch):
    monkeypatch.setattr(research_case_engine, "persist_state", lambda value: value)
    case = {"case_id": "c2", "objective": "Evaluate a technology upgrade", "objective_family": "TECHNOLOGY_FOR_NEXUS",
            "status": "UNDER_DEVELOPMENT", "owner_department": "UPGRADE_CONTROL"}
    result = research_case_engine._save(case, "SCHEMA_TEST")
    for field in ("case_type", "title", "parent_goal_id", "success_criteria", "current_phase", "current_owner",
                  "research_state", "systems_state", "labs_state", "finance_state", "evidence", "department_requests",
                  "department_results", "final_recommendation", "ray_decision_status", "completion_contract"):
        assert field in result
    assert result["upgrade_state"] == "ACTIVE"


def test_autonomous_research_continuation_prioritizes_case_bound_department_request():
    case = {
        "objective": "Old discovery question",
        "open_questions": [{"question_id": "old", "question": "What is the original idea?"}],
        "research_requests": [{"question_id": "new", "question": "Does free official market data permit company use?", "status": "OPEN"}],
        "department_requests": [{"request_id": "dept", "department": "RESEARCH",
                                 "requested_work": "Verify TSLA M30 feed coverage and licensing", "status": "OPEN"}],
    }
    question, department_request, case_request = research_case_engine._select_continuation_question(case)
    assert question == "Verify TSLA M30 feed coverage and licensing"
    assert department_request["request_id"] == "dept"
    assert case_request is None


def test_autonomous_research_continuation_prioritizes_case_research_request_over_old_question():
    case = {
        "objective": "Old discovery question",
        "open_questions": [{"question_id": "old", "question": "What is the original idea?"}],
        "research_requests": [{"question_id": "new", "question": "Does this free tier permit company use?", "status": "OPEN"}],
    }
    question, department_request, case_request = research_case_engine._select_continuation_question(case)
    assert question == "Does this free tier permit company use?"
    assert department_request is None
    assert case_request["question_id"] == "new"


def test_department_handoff_snapshot_is_json_serializable_and_not_circular(monkeypatch):
    original = {"case_id": "c3", "objective": "Validate a real strategy",
                "status": "MORE_RESEARCH_REQUIRED", "department_requests": [
                    {"request_id": "old", "department": "RESEARCH", "status": "RESULT_RETURNED"}
                ], "department_results": [], "sources": [], "findings": [], "syntheses": [],
                "hypotheses": [], "notebook_answers": [], "open_questions": []}
    captured = {}
    monkeypatch.setattr(research_case_engine, "get_case", lambda _: original)
    monkeypatch.setattr(research_case_engine, "_save", lambda _case, _event, **details: captured.update(details) or details)
    result = research_case_engine.request_department_work(
        "c3", department="MERCURY_TRADING", requested_work="Run a bounded historical replay",
        why_this_department="Trading owns strategy replay", expected_output="Metrics and limitations")
    assert result["ok"] is True
    import json
    json.dumps(captured["department_requests"])
    created = captured["department_requests"][-1]
    assert [row["request_id"] for row in created["what_already_happened"]["department_requests"]] == ["old"]


def test_failed_approach_is_recorded_without_failing_parent_objective(monkeypatch):
    original = {"case_id": "c4", "objective": "Develop a robust Wick strategy",
                "status": "MORE_RESEARCH_REQUIRED", "next_action": "TEST_ALTERNATIVE",
                "department_requests": [], "approaches": []}
    captured = {}
    monkeypatch.setattr(research_case_engine, "get_case", lambda _: original)
    monkeypatch.setattr(research_case_engine, "_save", lambda _case, event, **details: captured.update({"event": event, **details}) or details)
    result = research_case_engine.record_approach(
        "c4", approach_id="ema-transfer", description="EMA200 transfer to EUR/USD",
        why_considered="Notebook-recommended controlled test", status="NOT_RECOMMENDED",
        what_was_learned="Metrics weakened", why_not_recommended="Lower expectancy and PF",
        alternative_created="Test another OANDA-supported instrument")
    assert result["ok"] is True
    assert result["objective_preserved"] is True
    assert captured["objective_preserved"] is True
    assert captured["status"] == "MORE_RESEARCH_REQUIRED"
    assert captured["continue_research"] is True


def test_replan_case_keeps_objective_active_after_bad_approach(monkeypatch):
    original = {"case_id": "c5", "objective": "Determine whether Wick can be robust",
                "parent_objective": "Determine whether Wick can be robust", "status": "MORE_RESEARCH_REQUIRED",
                "approaches": [{"approach_id": "ema-transfer", "status": "NOT_RECOMMENDED"}]}
    captured = {}
    monkeypatch.setattr(research_case_engine, "get_case", lambda _: original)
    monkeypatch.setattr(research_case_engine, "_save", lambda _case, event, **details: captured.update({"event": event, **details}) or details)
    result = research_case_engine.replan_case(
        "c5", next_action="SELECT_OANDA_CROSS_PAIR_VALIDATION", next_owner="RESEARCH",
        selected_approach_id="oanda_cross_pair", reason="Continue after EMA transfer failed", trigger="RESULT_FEEDBACK")
    assert result["ok"] is True
    assert captured["parent_objective"] == original["objective"]
    assert captured["status"] == "REFINING"
    assert captured["next_action"] == "SELECT_OANDA_CROSS_PAIR_VALIDATION"


def test_autonomous_notebook_followup_selects_unanswered_high_value_issue():
    issue = "Can the original TradingView indicator signal be independently reconstructed to verify signal parity?"
    case = {
        "case_id": "wick-test", "notebook_id": "nb-test",
        "notebook_workspace": {"notebook_id": "nb-test"},
        "depth_budget": {"max_followup_questions": 2},
        "depth_used": {"followup_questions": 0},
        "notebook_answers": [{"prompt": "Assess real-volume route and signal parity.",
            "answer": "The strategy's volume method relies on a real centralized volume input; the OANDA tick volume is a proxy, so the real-volume route through Webull is preferred. The remaining issue is signal fidelity."}],
        "department_results": [{"result_id": "result-1", "department": "MERCURY_TRADING",
            "result": "OOS result remains negative.", "new_questions": [
                "Is the strategy dependent on centralized real volume rather than OANDA tick volume?", issue]}],
        "notebook_followup_cycles": [], "trading_development_plan": [],
    }
    selected = research_case_engine._select_autonomous_notebook_followup(case)
    assert selected is not None
    assert selected["issue"] == issue
    assert selected["question_type"] == "DATA_FIDELITY"
    assert selected["decision_relevant"] is True
    assert selected["test_can_answer_more_effectively"] is False


def test_autonomous_notebook_followup_obeys_depth_and_issue_dedupe():
    issue = "Can the source performance claim be independently verified?"
    case = {"notebook_id": "nb-test", "depth_budget": {"max_followup_questions": 1},
        "depth_used": {"followup_questions": 1}, "notebook_answers": [],
        "department_results": [{"new_questions": [issue]}], "notebook_followup_cycles": []}
    assert research_case_engine._select_autonomous_notebook_followup(case) is None
