from scripts.nova.nova_hermes_shadow import (
    _current_shadow_context,
    _shadow_resource_guidance,
)


def test_shadow_guidance_separates_discovery_from_verification():
    guidance = _shadow_resource_guidance()
    assert "discovery evidence" in guidance
    assert "public_web_retrieval_shadow" in guidance
    assert "simple fact" in guidance


def test_shadow_context_keeps_recent_conversation_and_marks_old_results_stale():
    context = _current_shadow_context({
        "active_request": "What did Research find?",
        "recent_turns": [{"user": "I chose option two", "assistant": "Option two is my recommendation."}],
        "resource_results": [{
            "capability": "alpha_challenge_shadow",
            "request_id": "old-request",
            "result_id": "old-result",
            "current_for_turn": False,
        }],
    })
    assert "I chose option two" in context
    assert '"current_for_turn": false' in context
    assert "What did Research find?" in context
