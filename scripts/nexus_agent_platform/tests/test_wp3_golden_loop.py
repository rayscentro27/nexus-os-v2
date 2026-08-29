from __future__ import annotations

import json

from nexus_agent_platform.wp3_golden_loop import _safe_status


def test_safe_status_rejects_credentials_and_pii_like_context():
    try:
        _safe_status({"email": "person@example.com"})
    except ValueError:
        pass
    else:
        raise AssertionError("PII-like context must be rejected")


def test_safe_status_accepts_synthetic_operational_context():
    value = _safe_status({"service": "synthetic", "health": "PASS", "count": 0})
    assert value["authority"] == "read_only"
    assert value["advisory"] is True


def test_executor_allowlist_is_deny_by_default():
    with open("reports/rebuild/NEXUS_PYTHON_EXECUTOR_ALLOWLIST.json", encoding="utf-8") as handle:
        payload = json.load(handle)
    assert payload["arbitrary_shell"] == "PROHIBITED"
    assert len(payload["executors"]) == 1


def test_bridge_review_budget_is_bounded():
    from nexus_agent_platform.bridge.oracle_hermes import BridgeRequest

    assert BridgeRequest(request_type="review", purpose="test", safe_context={}, max_tokens=96).max_tokens == 96
