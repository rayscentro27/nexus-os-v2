"""Tests for otel_adapter redaction — proves secrets and PII are removed."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from adapters.otel_adapter import _redact_text, _redact_metadata, _safe_hash


class TestRedactText:
    def test_bot_token(self):
        assert "REDACTED" in _redact_text("token: 1234567890:AAFabc123def456ghi789jkl012mno345pqr")
        assert "1234567890" not in _redact_text("token: 1234567890:AAFabc123def456ghi789jkl012mno345pqr")

    def test_email(self):
        redacted = _redact_text("send to ray@example.com please")
        assert "ray@example.com" not in redacted
        assert "REDACTED" in redacted

    def test_ssn(self):
        redacted = _redact_text("SSN: 123-45-6789")
        assert "123-45-6789" not in redacted
        assert "REDACTED" in redacted

    def test_stripe_key(self):
        from nexus_agent_platform.adapters.otel_adapter import _REDACT_PATTERNS
        stripe_pattern = next(p for p, _ in _REDACT_PATTERNS if 'sk_live' in p.pattern)
        fake_key = "sk_live_" + "A" * 24
        assert stripe_pattern.search("key: " + fake_key)
        assert not stripe_pattern.search("key: not_a_stripe_key")

    def test_openrouter_key(self):
        redacted = _redact_text("using sk-or-v1-abc123def456ghi789")
        assert "sk-or-v1-" not in redacted
        assert "REDACTED" in redacted

    def test_jwt_token(self):
        redacted = _redact_text("token: eyJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJzdXBhYmFzZSJ9.signature")
        assert "eyJ" not in redacted
        assert "REDACTED" in redacted

    def test_bearer_auth(self):
        redacted = _redact_text("Authorization: Bearer abc123def456ghi789jkl012mno")
        assert "Bearer" not in redacted or "REDACTED" in redacted

    def test_phone_number(self):
        redacted = _redact_text("call 555-123-4567")
        assert "555-123-4567" not in redacted

    def test_netlify_token(self):
        redacted = _redact_text("token: nfc_QLzBpNXekekTnKWhE9TrHab2FrwEQuYy9871")
        assert "nfc_" not in redacted

    def test_meta_token(self):
        redacted = _redact_text("EAAa2bxd5JsoBRrcw5j27FJT7oOiFimVudfYg")
        assert "EAAa2bxd5Jso" not in redacted

    def test_resend_key(self):
        # Uses the redaction regex directly to avoid GitHub secret-scanning false positives
        from nexus_agent_platform.adapters.otel_adapter import _REDACT_PATTERNS
        resend_pattern = next(p for p, _ in _REDACT_PATTERNS if 're_' in p.pattern)
        assert resend_pattern.search("key: re_EXAMPLE_1234567890abcdef")
        assert not resend_pattern.search("key: not_a_resend_key")

    def test_oanda_token(self):
        redacted = _redact_text("token: ae77b6c0effc9c6836b8085bab9318fc-d05ce7457fa2fd95f7aa9788d3036764")
        assert "ae77b6c0effc9c6836b8085bab9318fc" not in redacted

    def test_empty_string(self):
        assert _redact_text("") == ""

    def test_no_secrets(self):
        safe = "How many clients do we have?"
        assert _redact_text(safe) == safe

    def test_phone_us_format(self):
        redacted = _redact_text("call (555) 123-4567")
        assert "555" not in redacted or "REDACTED" in redacted


class TestRedactMetadata:
    def test_sensitive_keys(self):
        meta = {"bot_token": "secret123", "api_key": "key456", "normal": "safe"}
        result = _redact_metadata(meta)
        assert result["bot_token"] == "REDACTED"
        assert result["api_key"] == "REDACTED"
        assert result["normal"] == "safe"

    def test_chat_id_hashed(self):
        meta = {"chat_id": "1288928049"}
        result = _redact_metadata(meta)
        assert result["chat_id"] != "1288928049"
        assert len(result["chat_id"]) == 16  # sha256 truncated

    def test_user_id_hashed(self):
        meta = {"user_id": "999999999"}
        result = _redact_metadata(meta)
        assert result["user_id"] != "999999999"

    def test_nested_metadata(self):
        meta = {"outer": {"secret": "val", "safe": "ok"}}
        result = _redact_metadata(meta)
        assert result["outer"]["secret"] == "REDACTED"
        assert result["outer"]["safe"] == "ok"

    def test_string_values_redacted(self):
        meta = {"text": "email me at test@example.com"}
        result = _redact_metadata(meta)
        assert "test@example.com" not in result["text"]

    def test_empty_metadata(self):
        assert _redact_metadata({}) == {}
        assert _redact_metadata(None) == {}

    def test_non_string_values_preserved(self):
        meta = {"count": 42, "flag": True, "ratio": 3.14}
        result = _redact_metadata(meta)
        assert result["count"] == 42
        assert result["flag"] is True
        assert result["ratio"] == 3.14


class TestSafeHash:
    def test_deterministic(self):
        assert _safe_hash("1288928049") == _safe_hash("1288928049")

    def test_different_inputs(self):
        assert _safe_hash("111") != _safe_hash("222")

    def test_length(self):
        assert len(_safe_hash("test")) == 16

    def test_no_raw_value(self):
        h = _safe_hash("sensitive_id_12345")
        assert "sensitive_id_12345" not in h
