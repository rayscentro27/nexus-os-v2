from research_notebook_ownership import (
    DEDICATED_CANARY_FULL_CONTRACT,
    DEDICATED_CANARY_NEEDLE,
    DEDICATED_CANARY_V6,
    bounded_source_add_plan,
    classify_source_origin,
    dedicated_title,
    feeder_notebook_is_intake_only,
    find_dedicated_notebook,
    promotion_evidence_gap,
    source_delta,
    subject_key,
    validate_feeder_promotion,
    web_gap_query,
)


def test_feeder_notebook_is_intake_only():
    assert feeder_notebook_is_intake_only("FEEDER_NOTEBOOK")
    assert not feeder_notebook_is_intake_only("DEDICATED_RESEARCH")
    origin = classify_source_origin("YOUTUBE_CONTENT_SIGNAL", "BUSINESS_OPPORTUNITY_FEEDER")
    assert origin["intake_role"] == "FEEDER_INTAKE_ONLY"
    assert origin["requires_dedicated_notebook"] is True


def test_promoted_source_gets_subject_owned_dedicated_identity():
    assert dedicated_title("Lovable assisted app building") == dedicated_title("Lovable assisted app building")
    assert subject_key("Lovable assisted app building") != subject_key("Forex indicator strategy")


def test_unrelated_subjects_never_reuse_a_dedicated_notebook():
    notebook = {"id": "notebook-subject-a", "title": dedicated_title("Lovable app business")}
    assert find_dedicated_notebook([notebook], "Forex strategy") is None


def test_same_subject_reuses_exact_dedicated_notebook():
    notebook = {"id": "notebook-subject-a", "title": dedicated_title("Lovable app business")}
    assert find_dedicated_notebook([notebook], "Lovable app business") == notebook


def test_feeder_notebook_is_not_selected_as_dedicated_research():
    feeder = {"id": "mixed-feeder", "title": "Business Opportunity Feeder Notebook"}
    assert find_dedicated_notebook([feeder], "Lovable app business") is None


def test_feeder_promotion_requires_one_source_scoped_business_subject():
    promoted = validate_feeder_promotion({
        "classification": "BUSINESS_OPPORTUNITY",
        "promoted_subject": "AI-assisted small business website creation",
        "evidence_quote": "A source-grounded quote",
    }, expected_source_id="source-1", cited_source_ids=["source-1"])
    assert promoted["subject"] == "AI-assisted small business website creation"
    assert promoted["source_id"] == "source-1"


def test_feeder_promotion_rejects_cross_source_citations():
    import pytest
    with pytest.raises(ValueError, match="SOURCE_SCOPE_VIOLATION"):
        validate_feeder_promotion({
            "classification": "BUSINESS_OPPORTUNITY",
            "promoted_subject": "One coherent opportunity",
        }, expected_source_id="source-1", cited_source_ids=["source-1", "source-2"])


def test_feeder_promotion_rejects_non_promotable_sources():
    import pytest
    with pytest.raises(ValueError, match="NOT_PROMOTABLE"):
        validate_feeder_promotion({
            "classification": "NOT_PROMOTABLE",
            "promoted_subject": "Not a business",
        }, expected_source_id="source-1", cited_source_ids=["source-1"])


def test_promotion_gap_accepts_normalized_legacy_and_canonical_keys():
    assert promotion_evidence_gap({"material_evidence_gap":"  customer demand  is unverified "}) == "customer demand is unverified"
    assert promotion_evidence_gap({"evidence_gap":"pricing not established"}) == "pricing not established"


def test_missing_evidence_creates_scoped_web_research_query():
    query = web_gap_query("Lovable app business", "independent customer-demand evidence")
    assert "independent customer-demand evidence" in query
    assert "Lovable app business" in query
    assert "creator claims" in query


def test_gap_query_is_subject_specific_not_a_hard_coded_business_model():
    query = web_gap_query("mobile pet grooming marketplace", "regional demand and visible pricing")
    assert "mobile pet grooming marketplace" in query
    assert "regional demand and visible pricing" in query
    assert "AI-assisted custom web apps" not in query


def test_native_and_fallback_urls_are_added_to_the_same_notebook():
    native = bounded_source_add_plan("notebook-1", [
        {"title": "Official pricing", "url": "https://example.com/pricing"},
        {"title": "Bad URL", "url": "http://example.com"},
    ])
    fallback = bounded_source_add_plan("notebook-1", [
        {"title": "Search result", "url": "https://market.example/report"},
    ])
    assert native[0]["notebook_id"] == fallback[0]["notebook_id"] == "notebook-1"
    assert native[0]["url"] == "https://example.com/pricing"
    assert len(bounded_source_add_plan("notebook-1", [
        {"url": "https://one.example"}, {"url": "https://two.example"}, {"url": "https://three.example"}
    ], limit=5)) == 2


def test_source_count_delta_requires_real_new_source_id():
    before = [{"id": "youtube-source"}]
    after = [{"id": "youtube-source"}, {"id": "web-source"}]
    assert [row["id"] for row in source_delta(before, after)] == ["web-source"]


def test_bounded_canary_does_not_run_full_contract_needle_or_v6():
    assert DEDICATED_CANARY_FULL_CONTRACT is False
    assert DEDICATED_CANARY_NEEDLE is False
    assert DEDICATED_CANARY_V6 is False
