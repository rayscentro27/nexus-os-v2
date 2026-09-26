import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts" / "research"))
from research_v2_control_plane import (  # noqa: E402
    build_youtube_backfill,
    classify_completion,
    fair_select,
    project_questions,
    recover_youtube_channels,
)


def test_backfill_does_not_require_new_uploads():
    assert build_youtube_backfill(1) == [] or all(x["mode"] == "BACKFILL" for x in build_youtube_backfill(1))


def test_monitor_check_is_not_substantive():
    assert classify_completion({"processing_status": "DUPLICATE_UNCHANGED"}) == "MONITOR_CHECK_COMPLETE"


def test_assigned_channels_are_preserved():
    with tempfile.TemporaryDirectory() as directory:
        registry = Path(directory) / "alpha_source_registry.json"
        registry.write_text(json.dumps({"sources": [{
            "source_type": "YOUTUBE_CHANNEL",
            "source_url": "https://www.youtube.com/@example/videos",
            "source_name": "Example",
        }]}))
        channels = recover_youtube_channels(registry)
        assert channels and channels[0]["channel_name"] == "Example"


def test_project_questions_create_project_support_tasks():
    assert project_questions([{"project": "beta", "research_questions": ["What onboarding issue remains?"]}])[0]["program_id"] == "PROJECT_SUPPORT"


def test_research_more_is_bounded():
    tasks = [{"program_id": "RESEARCH_MORE"}, {"program_id": "SEO_SEARCH_INTELLIGENCE"}, {"program_id": "GITHUB_OPEN_SOURCE"}]
    assert fair_select(tasks, {"consecutive_research_more": 2}, 2)[0]["program_id"] != "RESEARCH_MORE"


def test_substantive_completion_requires_output():
    assert classify_completion({"processing_status": "FULLY_PROCESSED"}) == "EVIDENCE_INCOMPLETE"
    assert classify_completion({"processing_status": "FULLY_PROCESSED", "summary": "evidence"}) == "SUBSTANTIVE_COMPLETE"


def test_selection_is_not_analysis():
    assert classify_completion({"processing_status": "SELECTED"}) != "SUBSTANTIVE_COMPLETE"


def test_failure_is_local():
    assert classify_completion({"error": "transcript unavailable"}) == "FAILED_RETRYABLE"
