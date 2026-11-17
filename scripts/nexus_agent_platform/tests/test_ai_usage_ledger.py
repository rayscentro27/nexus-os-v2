"""Focused AI-usage ledger / governance tests (TEST_1..TEST_9).

Run isolated:
    PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest scripts/nexus_agent_platform/tests/test_ai_usage_ledger.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from nexus_agent_platform.runtime import ai_usage_ledger as led


@pytest.fixture()
def ledger(tmp_path, monkeypatch):
    store = tmp_path / "ai_usage" / "ledger.jsonl"
    monkeypatch.setenv(led.LEDGER_ENV, str(store))
    return store


def _records(store: Path):
    return [json.loads(l) for l in store.read_text().splitlines() if l.strip()]


# TEST_1 — Nova primary provider attempt creates an attributable event.
def test_nova_primary_attempt_attributable(ledger):
    ev = led.record_ai_usage(department="NOVA", agent="HERMES", job_id="job_t1",
                             provider="openai-codex", model="gpt-6.1-sol",
                             routing_reason="NOVA_CONVERSATION", success=True,
                             provider_status="HEALTHY")
    assert ev["EVENT_TYPE"] == "AI_USAGE"
    for k in ("DEPARTMENT", "AGENT", "PROVIDER", "MODEL", "ROUTING_REASON"):
        assert ev[k]
    assert ev["JOB_ID"] == "job_t1"
    assert ev["COST_CLASS"] == "INCLUDED_SUBSCRIPTION"


def test_unattributed_call_rejected(ledger):
    with pytest.raises(led.UnattributedAICallError):
        led.record_ai_usage(department="", agent="", provider="openai-codex",
                            model="x", routing_reason="")


# TEST_2 — Codex 429 creates a failed AI_USAGE event.
def test_codex_429_failed_event(ledger):
    ev = led.record_ai_usage(department="NOVA", agent="HERMES", job_id="job_t2",
                             provider="openai-codex", model="gpt-6.1-sol",
                             routing_reason="NOVA_CONVERSATION", success=False,
                             failure_reason="429 usage_limit_reached",
                             provider_status="USAGE_LIMIT_REACHED")
    assert ev["SUCCESS"] is False
    assert "usage_limit" in ev["FAILURE_REASON"]
    recs = [r for r in _records(ledger) if r.get("EVENT_TYPE") == "AI_USAGE"]
    assert any(r["SUCCESS"] is False for r in recs)


# TEST_3 — OpenRouter Free fallback is a separate successful event, FALLBACK_USED=YES.
def test_openrouter_fallback_separate_event(ledger):
    evs = led.record_nova_turn(job_id="job_t3", primary_provider="openai-codex",
                               primary_model="gpt-6.1-sol", primary_success=False,
                               primary_failure_reason="429 usage_limit_reached",
                               fallback_provider="openrouter",
                               fallback_model="nvidia/nemotron-3.5-super-vl:free",
                               fallback_tokens={"input": 18388, "output": 67, "total": 18455})
    assert len(evs) == 2
    primary, fb = evs
    assert primary["SUCCESS"] is False and primary["FALLBACK_USED"] is False
    assert fb["SUCCESS"] is True and fb["FALLBACK_USED"] is True
    assert fb["COST_CLASS"] == "FREE" and fb["ESTIMATED_COST"] == 0
    assert fb["TOTAL_TOKENS"] == 18455


# TEST_4 — Research provider call creates a DEPARTMENT=RESEARCH attributable event.
def test_research_attributable_event(ledger):
    ev = led.record_ai_usage(department="RESEARCH", agent="RESEARCH_INVESTIGATOR",
                             job_id="job_r4", work_item_id="wi_4",
                             provider="openai-codex", model="gpt-6.1-sol",
                             routing_reason="RESEARCH_MISSION", token_data="UNAVAILABLE")
    assert ev["DEPARTMENT"] == "RESEARCH"
    assert ev["TOKEN_DATA"] == "UNAVAILABLE"
    assert ev["TOTAL_TOKENS"] is None


# TEST_5 — Research repeated 429 does not create an uncontrolled immediate retry loop.
def test_research_retry_guard(ledger):
    # First exhaustion marks the provider blocked.
    led.note_provider_exhaustion("openai-codex", reason="429 usage_limit_reached")
    d = led.should_defer_retry("job_r5", "openai-codex", "gpt-6.1-sol",
                               prior_failure_reason="429 usage_limit_reached")
    assert d["defer"] is True
    assert d["action"] == "RETRY_DEFERRED"
    assert d["case_preserved"] is True
    assert d["resume_after"]


def test_retry_guard_proceeds_when_healthy(ledger):
    d = led.should_defer_retry("job_ok", "openrouter", "nvidia/nemotron-3.5-super-vl:free")
    assert d["defer"] is False and d["action"] == "PROCEED"


# TEST_6 — Provider exhaustion creates a durable alert.
def test_exhaustion_creates_durable_alert(ledger):
    res = led.raise_provider_alert("openai-codex", provider_status="USAGE_LIMIT_REACHED",
                                   reason="429 usage_limit_reached")
    assert res["raised"] is True and res["alert_level"] == "EXHAUSTED"
    alerts = [r for r in _records(ledger) if r.get("EVENT_TYPE") == "AI_PROVIDER_ALERT"]
    assert alerts and alerts[-1]["ALERT_LEVEL"] == "EXHAUSTED"
    assert set(alerts[-1]["VISIBLE_TO"]) == {"SYSTEMS", "NOVA", "RAY"}


def test_numeric_alert_thresholds(ledger):
    assert led.classify_alert(55) == "INFO"
    assert led.classify_alert(72) == "WATCH"
    assert led.classify_alert(88) == "WARNING"
    assert led.classify_alert(96) == "CRITICAL"
    assert led.classify_alert(100) == "EXHAUSTED"
    assert led.classify_alert(None) == "NONE"


# TEST_7 — Repeated identical exhaustion does not spam duplicate alerts.
def test_alert_dedup(ledger):
    first = led.raise_provider_alert("openai-codex", provider_status="USAGE_LIMIT_REACHED")
    second = led.raise_provider_alert("openai-codex", provider_status="USAGE_LIMIT_REACHED")
    assert first["raised"] is True
    assert second["raised"] is False and second["deduped"] is True
    alerts = [r for r in _records(ledger) if r.get("EVENT_TYPE") == "AI_PROVIDER_ALERT"]
    assert len(alerts) == 1


# TEST_8 — Nova can retrieve the usage summary.
def test_usage_summary_available(ledger):
    led.record_nova_turn(job_id="job_t8", primary_provider="openai-codex",
                         primary_model="gpt-6.1-sol", primary_success=False,
                         primary_failure_reason="429",
                         fallback_provider="openrouter",
                         fallback_model="nvidia/nemotron-3.5-super-vl:free",
                         fallback_tokens={"input": 10, "output": 5, "total": 15})
    s = led.usage_summary("today")
    assert s["TOTAL_REQUESTS"] >= 2
    assert s["FALLBACK_CALLS"] >= 1
    assert s["FAILED_PROVIDER_CALLS"] >= 1
    assert s["REQUESTS_BY_DEPARTMENT"].get("NOVA", 0) >= 2
    assert s["PRE_INSTRUMENTATION_TOKEN_TOTALS"] == "UNAVAILABLE"
    assert s["OPENROUTER_PAID_ENABLED"] == "NO"
    # weekly window also supported
    assert led.usage_summary("last_7_days")["TOTAL_REQUESTS"] >= 2


# TEST_9 — No paid OpenRouter route becomes enabled.
def test_paid_openrouter_disabled(ledger):
    # free model -> FREE/zero cost
    assert led.cost_class_for("openrouter", "nvidia/nemotron-3.5-super-vl:free") == "FREE"
    # a hypothetical paid model would classify PAID_METERED but is never enabled here
    assert led.cost_class_for("openrouter", "anthropic/claude-x") == "PAID_METERED"
    fb = led.record_ai_usage(department="NOVA", agent="HERMES", job_id="j9",
                             provider="openrouter", model="nvidia/nemotron-3.5-super-vl:free",
                             routing_reason="FALLBACK", total_tokens=10)
    assert fb["COST_CLASS"] == "FREE" and fb["ESTIMATED_COST"] == 0
