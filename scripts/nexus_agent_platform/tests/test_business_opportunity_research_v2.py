from __future__ import annotations

import json

from nexus_agent_platform import business_opportunity_research_v2 as bo
from nexus_agent_platform.research_work_queue import ResearchWorkQueue


def test_source_led_tiktok_shop_is_intake_only_and_matches_existing(tmp_path, monkeypatch):
    monkeypatch.setattr(bo, "CONTEXT_DIR", tmp_path)
    monkeypatch.setattr(bo, "CONTEXT_PATH", tmp_path / "opportunities.json")
    existing = {"opportunity_id": "tiktok-shop", "objective": "TikTok Shop product discovery sourcing fulfillment"}
    result = bo.build_intake(title="How to start TikTok Shop", source_url="https://youtube.com/watch?v=abc",
        source_type="YOUTUBE_VIDEO", contexts=[existing])
    assert result["entry_type"] == "SOURCE_LED"
    assert result["opportunity_relationship"] == "MATCH_EXISTING_OPPORTUNITY"
    assert result["feeder_role"] == "INTAKE_ONLY"
    assert result["dedicated_notebook_required_on_promotion"] is True


def test_tiktok_incremental_product_source_is_not_duplicate_opportunity():
    result = bo.build_intake(title="Top boring TikTok products", source_url="https://youtube.com/watch?v=p",
        source_type="YOUTUBE_VIDEO", contexts=[{"opportunity_id": "shop", "objective": "TikTok Shop products"}])
    assert result["source_role"] == "PRODUCT_DISCOVERY"
    assert result["opportunity_relationship"] == "MATCH_EXISTING_OPPORTUNITY"


def test_livestorebuild_vendor_requires_independent_reputation_branch():
    result = bo.build_intake(title="LiveStoreBuild ecommerce platform", vendor_name="LiveStoreBuild",
        source_url="https://livestorebuild.com")
    assert result["entry_type"] == "VENDOR_LED"
    assert result["independent_reputation_branch_required"] is True
    assert bo.classify_vendor_claim("refund claims", identity_match=False) == "ENTITY_MISMATCH"


def test_faceless_youtube_video_classifies_as_source_led_business_model():
    result = bo.build_intake(title="Faceless YouTube channel business model", source_type="YOUTUBE_VIDEO",
        source_url="https://youtube.com/watch?v=f")
    assert result["entry_type"] == "SOURCE_LED"
    assert result["source_role"] in {"BUSINESS_MODEL", "STRATEGY"}


def test_top3_objective_uses_existing_queue_idempotently(tmp_path):
    queue = ResearchWorkQueue(tmp_path / "queue.json")
    objective = "Find three low-cost online businesses with possible revenue within 30 days"
    first = bo.queue_top3_objective(queue, objective=objective, objective_id="owner-top3-1")
    second = bo.queue_top3_objective(queue, objective=objective, objective_id="owner-top3-1")
    assert first["status"] == "QUEUED"
    assert second["status"] == "REUSED"
    assert first["work_id"] == second["work_id"]
    assert len(queue.load()["items"]) == 1
    assert queue.load()["items"][0]["notebook_role"] == "NO_NOTEBOOK_UNTIL_FINALIST_PROMOTION"


def test_trend_fixture_preserves_relative_metric_and_filters_noncommercial_noise():
    row = bo.normalize_trend_signal({"signal_class": "GOOGLE_SEARCH_TREND", "topic": "example",
        "relative_growth": 240, "period": "this week", "geography": "US"})
    assert row["evidence_class"] == "TREND_SIGNAL_NOT_ABSOLUTE_SEARCH_VOLUME"
    assert row["absolute_volume"] is None
    assert bo.trend_disposition(commercial_intent="ENTERTAINMENT_ONLY", cause="CELEBRITY_SPIKE",
        existing_match={"relationship": "NEW_OPPORTUNITY"}, evidence_confidence="HIGH") == "TREND_NOT_COMMERCIAL_ARCHIVE"


def test_adaptive_followup_is_material_and_uncertainty_is_not_evidence():
    questions = bo.adaptive_discovery_candidates(finding={"finding": "supplier MOQ is 500 units"},
        opportunity={"opportunity_id": "o1"})
    assert len(questions) == 1
    assert questions[0]["evidence_status"] == "UNVERIFIED"
    assert questions[0]["materiality_topic"] == "sourcing"
    assert bo.validate_director_questions([{"question": "What color is the logo?", "materiality_topic": "curiosity"}]) == []


def test_opportunity_context_promotes_one_coherent_notebook_identity(tmp_path, monkeypatch):
    monkeypatch.setattr(bo, "CONTEXT_DIR", tmp_path)
    monkeypatch.setattr(bo, "CONTEXT_PATH", tmp_path / "opportunities.json")
    first = bo.promote_to_dedicated_research({"original_idea": "TikTok Shop pet products"},
        objective="Research TikTok Shop pet products", original_source={"url": "https://example.org"})
    second = bo.promote_to_dedicated_research({"original_idea": "TikTok Shop pet products", "notebook_id": "nb-1"},
        objective="Continue TikTok Shop pet products")
    unrelated = bo.promote_to_dedicated_research({"original_idea": "Local bookkeeping service"},
        objective="Research bookkeeping service")
    assert first["opportunity_id"] == second["opportunity_id"]
    assert first["notebook_subject_key"] == second["notebook_subject_key"]
    assert second["notebook_id"] == "nb-1"
    assert unrelated["opportunity_id"] != first["opportunity_id"]
    assert len(bo.load_opportunity_contexts()) == 2


def test_director_prompt_is_role_bounded_and_action_is_governed():
    prompt = bo.research_director_prompt(objective="Investigate", context={"opportunity_id": "o"})
    assert "ALPHA_MODE=RESEARCH_DIRECTOR" in prompt
    assert "Do not invent evidence" in prompt
    assert "post-research" not in prompt.lower()
    action = bo.create_research_action(action_type="QUOTE_REQUEST", target="supplier", questions_to_resolve=["MOQ?"],
        why_material="Changes startup cost")
    assert action["status"] == "RAY_ACTION_REQUIRED"
    assert action["approval_required"] is True


def test_director_uses_canonical_router_and_keeps_hypotheses_unverified(monkeypatch):
    import model_router
    seen = {}
    def fake_execute(**kwargs):
        seen.update(kwargs)
        return {"result": {"choices": [{"message": {"content": json.dumps({
            "candidate_questions": [{"question": "Can a lower-MOQ supplier improve economics?",
                "materiality_topic": "sourcing", "evidence_needed": "Compare written quotes"}]})}}]},
            "provider": "test-router", "model": "fixture", "cost_class": "TEST"}
    monkeypatch.setattr(model_router, "execute_reasoning", fake_execute)
    result = bo.execute_research_director(objective="Assess an opportunity", context={"opportunity_id": "o1"})
    assert seen["reasoning_class"] == "STRONG_REASONING"
    assert seen["task_type"] == "business_opportunity_research_director"
    assert result["alpha_mode"] == "RESEARCH_DIRECTOR"
    assert result["candidate_questions"][0]["evidence_status"] == "UNVERIFIED"


def test_economics_are_deterministic_and_not_guaranteed():
    result = bo.calculate_opportunity_economics(price=50, variable_cost=20, monthly_fixed_cost=300)
    assert result["contribution_per_sale"]["value"] == 30
    assert result["break_even_units"]["value"] == 10
    assert result["units_for_target_operating_profit"]["values"]["5000"] == 177
    assert result["profit_guaranteed"] is False


def test_compact_package_has_explicit_size_and_drops_unlisted_transcript():
    package = bo.build_opportunity_package({"opportunity_id": "o1", "summary": "short",
        "raw_transcript": "secret long transcript", "verified_findings": ["fact"]}, max_bytes=2000)
    assert "raw_transcript" not in package
    assert package["final_handoff_bytes"] == len(json.dumps(package, ensure_ascii=False,
        separators=(",", ":")).encode())


def test_intake_creates_reusable_local_opportunity_context(tmp_path, monkeypatch):
    monkeypatch.setattr(bo, "CONTEXT_DIR", tmp_path)
    monkeypatch.setattr(bo, "CONTEXT_PATH", tmp_path / "opportunities.json")
    intake=bo.build_intake(title="Online pet-care booking service",source_type="YOUTUBE_VIDEO",
        source_url="https://youtube.com/watch?v=pet-care")
    first=bo.prepare_opportunity_intake(intake=intake,objective="Online pet-care booking service",
        original_source={"url":"https://youtube.com/watch?v=pet-care"})
    saved=bo.save_opportunity_context({**first["context"],"research_case_id":"case-1","notebook_id":"nb-1"})
    follow=bo.build_intake(title="Pet-care bookings for clinics",source_type="YOUTUBE_VIDEO",
        source_url="https://youtube.com/watch?v=clinic",contexts=[saved])
    reused=bo.prepare_opportunity_intake(intake={**follow,"matched_opportunity_id":first["opportunity_id"]},
        objective="Pet-care bookings for clinics")
    assert reused["opportunity_id"]==first["opportunity_id"]
    assert reused["context"]["notebook_id"]=="nb-1"
    assert reused["context"]["research_case_id"]=="case-1"


def test_trend_routes_pattern_and_includes_tiktok_format():
    signal=bo.normalize_trend_signal({"signal_class":"TIKTOK_FORMAT_TREND","topic":"short demo format",
        "relative_growth":90})
    assert signal["evidence_class"]=="TREND_SIGNAL_NOT_ABSOLUTE_SEARCH_VOLUME"
    assert bo.route_trend_signal(signal_class=signal["signal_class"],commercial_intent="PRESENT",
        cause="NEW_PLATFORM_BEHAVIOR",existing_match={"relationship":"NEW_OPPORTUNITY"},
        evidence_confidence="MEDIUM",format_signal=True)=="MARKETING_PATTERN"


def test_vendor_reputation_branch_is_explicit_and_entity_resolved():
    rows=bo.vendor_reputation_questions("Acme Widget")
    assert len(rows)>=4
    assert all(row["branch"]=="INDEPENDENT_REPUTATION_RESEARCH" for row in rows)
    assert any("similarly named" in row["question"] for row in rows)


def test_group_checkpoint_reuses_queue_item_and_deduplicates_adaptive_question(tmp_path):
    queue = ResearchWorkQueue(tmp_path / "queue.json")
    queue.enqueue(work_id="source-1", work_class="ASSIGNED", source_type="YOUTUBE_VIDEO",
        source_id="video-1", opportunity_id="opp-1", source_url="https://youtube.com/watch?v=video-1")
    first = bo.checkpoint_research_group(queue, work_id="source-1", notebook_id="dedicated-nb",
        question_statuses=[{"question_id": "BO_Q1", "asked": True, "evidence_status": "PARTIALLY_VERIFIED",
            "answer": "raw answer excluded"}], findings=[{"finding": "supplier MOQ is 500 units"}])
    second = bo.checkpoint_research_group(queue, work_id="source-1", notebook_id="dedicated-nb",
        question_statuses=[{"question_id": "BO_Q1", "asked": True, "evidence_status": "PARTIALLY_VERIFIED"}],
        findings=[{"finding": "supplier MOQ is 500 units"}])
    assert first["queue_item"]["notebook_id"] == "dedicated-nb"
    assert len(first["new_adaptive_questions"]) == 1
    assert second["new_adaptive_questions"] == []
    assert len(second["queue_item"]["discovery_questions"]) == 1
    assert "raw answer excluded" not in json.dumps(second["queue_item"]["research_checkpoint"])
