#!/usr/bin/env python3
"""
Shared Recommendation Layer Tests — Validates schema, scoring, ingestion, and cross-source consistency.

Run: python3 -m pytest tests/test_shared_recommendations.py -v
"""

import os
import sys
import json
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "recommendations"))
from recommendation_schema import (
    new_recommendation,
    score_dimensions_from_alpha,
    score_dimensions_from_hermes,
    save_recommendations,
    load_recommendations,
    append_recommendation,
    update_recommendation,
    get_recommendations,
    get_top_recommendations,
    add_follow_up_event,
    SCORING_DIMENSIONS,
)
from recommendation_engine import (
    ingest_alpha,
    ingest_hermes,
    ingest_nexus,
    get_prioritized,
    next_steps,
    summary,
    mark_status,
)


@pytest.fixture
def tmp_recs_file(monkeypatch, tmp_path):
    """Use a temp file for recommendation storage during tests."""
    rec_file = tmp_path / "recommendations.json"
    monkeypatch.setattr("recommendation_schema.RECOMMENDATIONS_FILE", str(rec_file))
    monkeypatch.setattr("recommendation_schema.RECOMMENDATIONS_HISTORY_DIR", str(tmp_path / "history"))
    return rec_file


class TestSchema:
    def test_new_recommendation_has_required_fields(self, tmp_recs_file):
        rec = new_recommendation(
            title="Test recommendation",
            source="alpha",
            topic="credit monitoring",
        )
        assert rec["id"].startswith("rec_")
        assert rec["title"] == "Test recommendation"
        assert rec["source"] == "alpha"
        assert rec["status"] == "new"
        assert rec["composite_score"] >= 0
        assert rec["composite_score"] <= 10
        assert isinstance(rec["scores"], dict)
        assert isinstance(rec["follow_up"], dict)

    def test_scoring_dimensions_cover_all_7(self):
        assert len(SCORING_DIMENSIONS) == 7
        for dim, spec in SCORING_DIMENSIONS.items():
            assert "min" in spec
            assert "max" in spec
            assert "description" in spec

    def test_scores_are_clamped(self, tmp_recs_file):
        rec = new_recommendation(
            title="Clamp test",
            source="test",
            scores={"speed_to_value": 15, "risk_adjustment": -10},
        )
        assert rec["scores"]["speed_to_value"] == 10
        assert rec["scores"]["risk_adjustment"] == -3

    def test_composite_score_weighted(self, tmp_recs_file):
        rec = new_recommendation(
            title="Weighted test",
            source="test",
            scores={
                "speed_to_value": 8,
                "cost_to_execute": 8,
                "fit_goclear": 9,
                "fit_nexus": 7,
                "ease_of_execution": 6,
                "proof_quality": 5,
                "risk_adjustment": 1,
            },
        )
        # Composite is weighted average: fit_goclear 1.5x, ease 0.8x, proof 0.7x
        assert rec["composite_score"] > 6.0  # clearly above midpoint
        assert rec["composite_score"] < 10.0  # not maxed out

    def test_priority_auto(self, tmp_recs_file):
        high = new_recommendation(
            title="High",
            source="test",
            scores={k: 10 for k in SCORING_DIMENSIONS},
            priority="auto",
        )
        low = new_recommendation(
            title="Low",
            source="test",
            scores={k: 1 for k in SCORING_DIMENSIONS},
            priority="auto",
        )
        assert high["priority"] == "high"
        assert low["priority"] == "low"


class TestDimensionMapping:
    def test_alpha_dimensions_mapped_to_7(self):
        alpha_scores = {
            "speed_to_value": 8,
            "cost": 9,
            "difficulty": 7,
            "risk": 8,
            "relevance": 6,
        }
        mapped = score_dimensions_from_alpha(alpha_scores)
        assert len(mapped) == 7
        assert mapped["speed_to_value"] == 8
        assert mapped["cost_to_execute"] == 9
        assert mapped["ease_of_execution"] == 7
        assert mapped["risk_adjustment"] >= -3
        assert mapped["risk_adjustment"] <= 3

    def test_hermes_dimensions_mapped_to_7(self):
        hermes_scores = {
            "speed_to_money": 7,
            "cost_to_try": 8,
            "fit_for_goclear": 9,
            "fit_for_nexus": 6,
            "ease_of_execution": 5,
            "proof_source_quality": 4,
            "risk_adjustment": 1,
        }
        mapped = score_dimensions_from_hermes(hermes_scores)
        assert len(mapped) == 7
        assert mapped["speed_to_value"] == 7
        assert mapped["cost_to_execute"] == 8
        assert mapped["fit_goclear"] == 9
        assert mapped["fit_nexus"] == 6
        assert mapped["proof_quality"] == 4


class TestPersistence:
    def test_save_and_load(self, tmp_recs_file):
        recs = [
            new_recommendation("Rec A", "alpha"),
            new_recommendation("Rec B", "hermes"),
        ]
        save_recommendations(recs)
        loaded = load_recommendations()
        assert len(loaded) == 2
        assert loaded[0]["title"] == "Rec A"

    def test_append_dedup(self, tmp_recs_file):
        rec = new_recommendation("Dedup test", "alpha")
        append_recommendation(rec)
        append_recommendation(rec)  # same title+source, within 24h
        loaded = load_recommendations()
        assert len(loaded) == 1

    def test_append_different_source_not_deduped(self, tmp_recs_file):
        rec_alpha = new_recommendation("Same title", "alpha")
        rec_hermes = new_recommendation("Same title", "hermes")
        append_recommendation(rec_alpha)
        append_recommendation(rec_hermes)
        loaded = load_recommendations()
        assert len(loaded) == 2


class TestIngestion:
    def test_ingest_alpha(self, tmp_recs_file):
        ideas = [
            {"title": "Idea 1", "why": "Because", "action": "Do it",
             "score": {"total": 7.5, "dimensions": {"speed_to_value": 8, "cost": 7, "difficulty": 6, "risk": 7, "relevance": 8}}},
            {"title": "Idea 2", "why": "Also good", "action": "Try it",
             "score": {"total": 6.0, "dimensions": {"speed_to_value": 5, "cost": 6, "difficulty": 7, "risk": 6, "relevance": 7}}},
        ]
        recs = ingest_alpha("credit tools", ideas, 6.75, category="client_acquisition")
        assert len(recs) == 2
        assert all(r["source"] == "alpha" for r in recs)
        assert recs[0]["composite_score"] >= recs[1]["composite_score"]

    def test_ingest_hermes(self, tmp_recs_file):
        advisory = {
            "answer": "Found 3 tools",
            "search_status": "ok",
            "findings": [{"title": "Tool A", "url": "http://a.com", "snippet": "...", "score": 8.0}],
            "why_it_matters": ["High potential"],
            "next_step": "Review findings",
        }
        search_result = {"status": "ok", "provider": "brave"}
        rec = ingest_hermes("best credit tools", search_result, advisory)
        assert rec["source"] == "hermes"
        assert rec["composite_score"] > 0

    def test_ingest_nexus(self, tmp_recs_file):
        rec = ingest_nexus("Upgrade monitoring", "System needs better alerting", priority="high")
        assert rec["source"] == "nexus"
        assert rec["priority"] == "high"


class TestQuerying:
    def test_get_prioritized_sorted(self, tmp_recs_file):
        ingest_nexus("Low priority item", priority="low")
        ingest_nexus("High priority item", priority="high")
        top = get_prioritized(limit=1)
        assert len(top) == 1

    def test_filter_by_source(self, tmp_recs_file):
        ingest_alpha("Alpha topic", [
            {"title": "A1", "why": "...", "action": "...", "score": {"total": 5, "dimensions": {"speed_to_value": 5, "cost": 5, "difficulty": 5, "risk": 5, "relevance": 5}}}
        ], 5.0)
        ingest_nexus("Nexus item")
        alpha_only = get_recommendations(source="alpha")
        assert all(r["source"] == "alpha" for r in alpha_only)

    def test_summary(self, tmp_recs_file):
        ingest_nexus("Summary test")
        s = summary()
        assert s["total"] >= 1
        assert "by_status" in s
        assert "by_source" in s


class TestFollowUp:
    def test_mark_status(self, tmp_recs_file):
        ingest_nexus("Follow-up test")
        recs = load_recommendations()
        rec_id = recs[0]["id"]
        updated = mark_status(rec_id, "approved")
        assert updated["status"] == "approved"

    def test_add_follow_up_event(self, tmp_recs_file):
        ingest_nexus("Event test")
        recs = load_recommendations()
        rec_id = recs[0]["id"]
        add_follow_up_event(rec_id, "checked", "Looked at it")
        updated = load_recommendations()
        rec = [r for r in updated if r["id"] == rec_id][0]
        assert len(rec["follow_up"]["history"]) >= 1
        assert rec["follow_up"]["attempts"] >= 1
