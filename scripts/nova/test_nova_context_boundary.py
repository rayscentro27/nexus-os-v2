from nova_hermes_shadow import _conversation_history_for_model


def test_resource_backed_history_is_labeled_as_non_current_context():
    history = _conversation_history_for_model({
        "recent_turns": [{
            "user": "Check Nexus and tell me what needs my attention.",
            "assistant": "There are no current blockers.",
            "source_type": "RESOURCE_BACKED",
            "resource_domains": ["NEXUS"],
        }],
    })

    assert history[0] == {
        "role": "user",
        "content": "Check Nexus and tell me what needs my attention.",
    }
    assert "PRIOR RESOURCE-BACKED RESPONSE" in history[1]["content"]
    assert "not current operational truth" in history[1]["content"]


def test_legacy_history_is_retained_but_not_promoted_to_resource_truth():
    history = _conversation_history_for_model({
        "recent_turns": [{
            "user": "What happened before?",
            "assistant": "A historical research count was recorded.",
        }],
    })

    assert "A historical research count was recorded." in history[1]["content"]
    assert "not a current resource result" in history[1]["content"]
