from executive_intelligence import classify_query, decompose_question, decision_framework, process_record, specialist_selection, telegram_executive_format


BENCHMARK_QUESTIONS = [
    "What items currently need my review?",
    "What should Nexus focus on today and why?",
    "What changed since the last operating cycle?",
    "What is actually blocking GoClear?",
    "Should the $97 Funding Readiness offer remain paid?",
    "What would happen economically if we made the readiness assessment free?",
    "Should GoClear have a monthly subscription?",
    "Which opportunity deserves the next experiment and why?",
    "Our Trading strategy failed promotion. What should happen next?",
    "How healthy is Nexus right now, and what concerns you?",
    "What do Research and Alpha disagree about?",
    "What should I approve today versus what Nexus can continue without me?",
    "We want to launch GoClear. What dependencies still exist?",
    "Give me a plan involving Research, Finance, Marketing and Creative.",
    "Compare two possible GoClear revenue models and recommend one.",
    "An opportunity has strong potential but poor evidence. What should we do?",
    "Trading has positive metrics but only two OOS trades. Is that good?",
    "Creative produced three campaign ideas. Which should we test first?",
    "We have three important goals and limited resources. Prioritize them.",
    "Take this recommendation and turn it into an executable multi-department process.",
]


def test_twenty_case_executive_benchmark_has_depth_routing():
    plans = [decompose_question(q) for q in BENCHMARK_QUESTIONS]
    assert len(plans) == 20
    assert sum(p["complexity"] == "MULTI_LEVEL_STRATEGIC_QUERY" for p in plans) >= 7
    assert sum(len(p["specialists"]) >= 2 for p in plans) >= 6
    assert all(p["goal_completion_rule"] for p in plans)


def test_simple_and_current_queries_do_not_over_orchestrate():
    assert classify_query("What is 2 + 2?") == "SIMPLE_FACT"
    assert classify_query("What is the current Nexus status?") == "CURRENT_STATE_QUERY"
    assert specialist_selection("What is the current Nexus status?") == ["RESEARCH", "SYSTEMS"]


def test_decision_and_mobile_contracts_are_compact_and_truthful():
    decision = decision_framework("Should the offer change?")
    assert decision["confidence"] == "UNKNOWN"
    assert decision["recommended_option"] is None
    message = telegram_executive_format("Recommend a bounded test.", why="It is reversible.", decision="Approve internal preparation")
    assert message.startswith("Recommend a bounded test.")
    assert "Ray decision:" in message


def test_durable_process_record_is_parent_owned(tmp_path, monkeypatch):
    import executive_intelligence as module
    monkeypatch.setattr(module, "PROCESS_DIR", tmp_path)
    plan = decompose_question("Turn this recommendation into an executable multi-department process")
    record = process_record("nova-test-session", "Turn this recommendation into an executable multi-department process", plan, result="Research pending")
    assert record["status"] == "ADVANCING"
    assert record["next_action"]
    assert record["plan"]["complexity"] == "DURABLE_PROCESS_REQUEST"
