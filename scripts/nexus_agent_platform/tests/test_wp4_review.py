from nexus_agent_platform.loops import review


def test_hermes_review_is_bounded_and_sanitized(monkeypatch):
    seen = {}

    class Result:
        returncode = 0
        stdout = "REVIEW_OK\n"

    def fake_run(command, **kwargs):
        seen["command"] = command
        seen["kwargs"] = kwargs
        return Result()

    monkeypatch.setattr(review.subprocess, "run", fake_run)
    result = review.hermes_advisory_review({"secret": "not passed"})
    assert result["status"] == "PASS"
    assert "--cli" in " ".join(seen["command"])
    assert seen["kwargs"]["timeout"] == 30
    assert all("api_key" not in part.lower() for part in seen["command"])
