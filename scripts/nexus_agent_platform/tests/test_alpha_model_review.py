from nexus_agent_platform.alpha_model_review import _normalize_need


def test_model_review_normalizes_short_need_into_governed_shape():
    package = {
        "query": "new LLC funding denials and documentation",
        "analysis": {"summary": "Public sources discuss repeated funding denials."},
    }
    need = _normalize_need(
        {"need": "New LLC owners need clearer funding guidance.", "confidence": "HIGH"},
        package,
        ["https://example.com/a", "https://youtube.com/watch?v=1"],
    )
    assert need["audience"]
    assert need["question"] == package["query"]
    assert need["source_refs"] == ["https://example.com/a", "https://youtube.com/watch?v=1"]
    assert need["confidence"] == "HIGH"
