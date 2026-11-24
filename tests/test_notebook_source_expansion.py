from scripts.research.notebook_source_expansion import (group_gaps, recommend_method, source_quality,
    qualify_candidate, evaluate_gap_evidence, canonical_source_url, _sensitive_public_query)
from scripts.nexus_agent_platform.research_work_queue import ResearchWorkQueue


def test_method_router_prefers_notebook_for_lender_verification():
    assert recommend_method("What are the lender credit score and checking requirements?", notebook_reference="nb-1") == "NOTEBOOKLM_FAST_RESEARCH"
    assert recommend_method("What is the customer demand and competitor landscape?", notebook_reference="nb-1") == "NOTEBOOKLM_DEEP_RESEARCH"
    assert recommend_method("Can we query historical option chain API data?", notebook_reference="nb-1") == "NEXUS_EXTERNAL_RESEARCH"


def test_related_first_citizens_gaps_group_and_keep_exact_questions():
    rows = [{"question_id": "q1", "source_id": "s1", "notebook_reference": "nb", "question": "What credit requirements are required?"},
            {"question_id": "q2", "source_id": "s1", "notebook_reference": "nb", "question": "What documentation does the lender require?"}]
    batch = group_gaps(rows)
    assert len(batch) == 1
    assert batch[0]["exact_questions"] == [r["question"] for r in rows]
    assert batch[0]["can_one_pass_close_multiple_gaps"] is True


def test_source_rank_never_upgrades_creator_claim():
    assert source_quality("https://www.firstcitizens.com/line") == "PRIMARY_OFFICIAL"
    assert source_quality("https://www.youtube.com/watch?v=x") == "DISCOVERY_ONLY"


def test_lender_requirement_sources_must_be_on_the_lenders_official_domain():
    domains = {"www.firstcitizens.com"}
    government = qualify_candidate(question="First Citizens credit score requirements", title="Credit score rules",
        url="https://www.consumerfinance.gov/credit-rules", existing_urls=set(), existing_titles=set(),
        lender_specific=True, official_domains=domains)
    lender = qualify_candidate(question="First Citizens business credit requirements", title="Business credit requirements",
        url="https://www.firstcitizens.com/small-business/credit-financing/business-financing", existing_urls=set(),
        existing_titles=set(), lender_specific=True, official_domains=domains)
    assert government["source_quality"] == "PRIMARY_OFFICIAL"
    assert government["source_quality_pass"] is False
    assert lender["source_quality_pass"] is True


def test_candidate_filter_rejects_duplicates_and_private_data_queries():
    duplicate = qualify_candidate(question="business credit financing", title="Business financing",
        url="https://www.firstcitizens.com/business-financing", existing_urls={"https://www.firstcitizens.com/business-financing"},
        existing_titles={"business financing"})
    assert duplicate["duplicate"] is True
    assert _sensitive_public_query("Please verify this client's credit report") is True
    tracking_duplicate = qualify_candidate(question="business financing", title="Other display title",
        url="https://www.firstcitizens.com/business-financing/?utm_source=research", existing_urls={"https://www.firstcitizens.com/business-financing"}, existing_titles=set())
    assert tracking_duplicate["duplicate"] is True
    assert canonical_source_url("https://WWW.FIRSTCITIZENS.COM/business-financing/?utm_source=x#top") == "https://www.firstcitizens.com/business-financing"


def test_candidate_relevance_requires_specific_overlap():
    irrelevant = qualify_candidate(question="First Citizens business credit line requirements", title="USDA housing credit handbook",
        url="https://www.rd.usda.gov/credit-handbook", existing_urls=set(), existing_titles=set(),
        lender_specific=True, official_domains={"www.firstcitizens.com"})
    assert irrelevant["relevance_pass"] is False


def test_official_bank_credit_card_page_cannot_qualify_for_line_of_credit_pricing():
    candidate = qualify_candidate(question="What evidence establishes pricing for this business line of credit?",
        title="Rewards Business Visa Pricing Information", url="https://www.firstcitizens.com/small-business/credit-financing/credit-cards/rewards/pricing",
        existing_urls=set(), existing_titles=set(), lender_specific=True,
        official_domains={"www.firstcitizens.com"}, product="Business Line of Credit")
    assert candidate["source_quality"] == "PRIMARY_OFFICIAL"
    assert candidate["source_quality_pass"] is True
    assert candidate["relevance_pass"] is False


def test_broad_requirements_gap_can_close_with_verified_scope_while_specific_gaps_remain():
    answer = "Underwriting evaluates business experience and cash flow [1]. Minimum score is not published."
    source = [{"source_quality":"PRIMARY_OFFICIAL", "evidence_eligible":True}]
    assert evaluate_gap_evidence("What evidence establishes current requirements for this product?", answer, source) == "VERIFIED"
    assert evaluate_gap_evidence("What evidence establishes a minimum credit score?", answer, source) == "RESEARCH_REQUIRED"
    assert evaluate_gap_evidence("What evidence establishes current requirements?",
        "Status: VERIFIED. Official factors are listed [1-3]. Minimum score not published.", source) == "VERIFIED"


def test_research_required_attempt_does_not_close_feeder_gap(monkeypatch):
    import sys
    sys.path.insert(0, "scripts")
    import nexus_agent_platform.feeder_runtime as runtime

    calls = []
    class StubQueue:
        def load(self):
            return {"items": [{"work_id":"q-open", "request_type":"FEEDER_GAP_CLOSURE", "status":"COMPLETE",
                "last_result":{"evidence_state":"RESEARCH_REQUIRED", "gap_state":"IN_PROGRESS"}}]}

    def fake_request(path, method="GET", payload=None, prefer=None):
        calls.append((path, method))
        if path.startswith("nexus_feeder_research_gaps?status=in."):
            return [{"question_id":"q-open", "source_id":"s-open", "status":"IN_PROGRESS"}]
        return []

    monkeypatch.setattr(runtime, "_request", fake_request)
    monkeypatch.setattr(runtime, "create_handoff", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not hand off")))
    import nexus_agent_platform.research_work_queue as queue_module
    monkeypatch.setattr(queue_module, "ResearchWorkQueue", StubQueue)
    result = runtime.sync_research_returns()
    assert result["completed_gap_count"] == 0
    assert not any(method == "PATCH" for _, method in calls)


def test_research_queue_preserves_notebook_route_metadata():
    item = ResearchWorkQueue.normalize({"work_id": "q1", "work_class": "ASSIGNED", "request_type": "FEEDER_GAP_CLOSURE",
        "notebook_reference": "nb-1", "exact_research_question": "What are the current requirements?",
        "recommended_research_method": "NOTEBOOKLM_FAST_RESEARCH"})
    assert item["notebook_reference"] == "nb-1"
    assert item["exact_research_question"] == "What are the current requirements?"
    assert item["recommended_research_method"] == "NOTEBOOKLM_FAST_RESEARCH"
