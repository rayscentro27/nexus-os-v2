from nova_hermes_shadow import _conversation_history_for_model, _prior_records_for_turn


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
    assert "PRIOR RESOURCE-BACKED EXCHANGE" in history[1]["content"]
    assert "retrieve fresh state for facts" in history[1]["content"]


def test_legacy_history_is_retained_but_not_promoted_to_resource_truth():
    history = _conversation_history_for_model({
        "recent_turns": [{
            "user": "What happened before?",
            "assistant": "A historical research count was recorded.",
        }],
    })

    assert "A historical research count was recorded." not in history[1]["content"]
    assert "facts require current evidence" in history[1]["content"]


def test_active_referent_outranks_unrelated_later_resource_history():
    records = [
        {"capability": "mcp_google_mcp_gmail_search", "request_id": "gmail-a"},
        {"capability": "mcp_google_mcp_calendar_search_events", "request_id": "calendar-b"},
    ]
    ordered = _prior_records_for_turn(
        {"active_referent": {"capability": "mcp_google_mcp_gmail_search"}}, records
    )
    assert [row["request_id"] for row in ordered] == ["calendar-b", "gmail-a"]
