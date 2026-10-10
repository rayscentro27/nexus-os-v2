from nexus_agent_platform.research_quality import assess_run, build_market_cluster


def test_zero_weak_results_are_inconclusive_not_disproof():
    objective = {"research_question": "What unmet customer need is recurring?",
                 "evidence_needed": "Firsthand reports plus alternatives",
                 "best_source_classes": ["CUSTOMER_DISCUSSIONS"]}
    result = {"status": "COMPLETED", "queries": ["customer need"], "records": [],
              "qualified_findings_created": 0}
    quality = assess_run(objective, result)
    assert quality["execution_status"] == "PASS"
    assert quality["research_conclusion"] == "RESEARCH_INCONCLUSIVE"
    assert quality["next_research_action"] == "CHANGE_SOURCE_STRATEGY"


def test_raw_discovery_cases_do_not_count_as_supported_findings():
    objective = {"research_question": "What can improve Trading?",
                 "best_source_classes": ["TRADINGVIEW_PUBLIC_SCRIPTS"]}
    result = {"status": "COMPLETED", "queries": ["x"], "qualified_findings_created": 3,
              "records": [{"url": "https://www.tradingview.com/script/x/", "source_class": "TRADINGVIEW_PUBLIC_SCRIPTS"}]}
    assert assess_run(objective, result)["research_conclusion"] == "RESEARCH_INCONCLUSIVE"


def test_market_cluster_requires_independent_sources_and_source_classes():
    one = build_market_cluster("theme", [{"url": "https://a.example/1"}])
    assert one["cluster_eligibility"] == "INSUFFICIENT_SINGLE_OR_WEAK_SOURCE"
    assert one["source_count"] == 1
    assert one["source_diversity"] == 1
    assert one["next_research_action"] == "CHANGE_SOURCE_STRATEGY"
    enough = build_market_cluster("theme", [
        {"url": "https://reddit.com/a", "source_class": "CUSTOMER_DISCUSSIONS"},
        {"url": "https://amazon.com/b", "source_class": "PRODUCT_REVIEWS"},
        {"url": "https://youtube.com/c", "source_class": "DESIGNATED_YOUTUBE"},
    ])
    assert enough["cluster_eligibility"] == "ELIGIBLE_FOR_REVIEW"
    assert enough["source_count"] == 3
    assert enough["source_diversity"] == 3
    assert len(enough["firsthand_signals"]) == 1
    assert len(enough["product_signals"]) == 1
    assert len(enough["social_signals"]) == 1
