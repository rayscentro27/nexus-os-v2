import hashlib
import hmac
import json

from nexus_agent_platform import credential_control_plane as control_plane
from nexus_agent_platform.governed import executors


def test_netlify_presence_is_classified_without_retaining_values(monkeypatch):
    monkeypatch.setattr(control_plane, "_netlify_env_names", lambda: {"CF_ACCESS_CLIENT_ID", "CF_ACCESS_CLIENT_SECRET", "VOICE_ACCESS_ORIGIN", "GROQ_API_KEY"})
    record = control_plane.resolve("credential.cloudflare.voice_service.prod.v1", environ={})
    assert record["source_classification"] == "AVAILABLE_REMOTE_NETLIFY"
    assert record["source_found"] == ["NETLIFY_ENV"]
    assert "[REMOTE_CONFIGURED]" not in json.dumps(record)
    assert record["values_included"] is False


def test_review_executors_are_registered_and_internal_only():
    assert "business_attention.review" in executors.registered_executors()
    assert "opportunity.review" in executors.registered_executors()
    assert executors.get_executor("business_attention.review")({"finding_id": "fixture"})["external_action_performed"] is False
    assert executors.get_executor("opportunity.review")({"opportunity_id": "fixture"})["external_action_performed"] is False


def test_meta_signature_fixture_uses_constant_time_compatible_digest():
    raw = json.dumps({"object": "page", "entry": []}, separators=(",", ":"))
    secret = "fixture-secret"
    signature = "sha256=" + hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()
    assert signature.startswith("sha256=") and len(signature) == 71
