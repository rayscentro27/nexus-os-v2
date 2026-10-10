from __future__ import annotations

import pytest

from nexus_agent_platform.provider_enforcement import (
    authorize_browser_action, authorize_email_action, authorize_social_action,
    authorize_telegram_action, classify_browser_action, classify_email_action,
    classify_social_action, execute, execute_telegram_delivery,
)
from nexus_agent_platform.resource_spend_governor import GovernanceDenied, LocalGovernorStore


def test_unknown_paid_provider_is_denied_before_action_and_footprinted(tmp_path, monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNOR_DB", str(tmp_path / "gov.sqlite3"))
    monkeypatch.setenv("NEXUS_DEPARTMENT", "TEST")
    called = []
    with pytest.raises(GovernanceDenied):
        execute("UNREGISTERED_PAID_SERVICE", "unknown", "GENERATE", {"requests": 1, "cost": 1, "billable": True},
                lambda: called.append(True), job_id="unknown-provider-job", correlation_id="test-correlation")
    assert called == []
    row = LocalGovernorStore(tmp_path / "gov.sqlite3").connect()
    with row as db:
        incident = db.execute("SELECT code FROM incidents WHERE job_id=?", ("unknown-provider-job",)).fetchone()
        footprint = db.execute("SELECT payload FROM footprints WHERE job_id=?", ("unknown-provider-job",)).fetchone()
    assert incident and footprint
    assert "HUMAN_APPROVAL_REQUIRED" in footprint[0]


def test_provider_calls_require_durable_job_identity_before_governor_or_action(monkeypatch):
    monkeypatch.delenv("NEXUS_DURABLE_JOB_ID", raising=False)
    called = []
    with pytest.raises(GovernanceDenied, match="DURABLE_JOB_ID_REQUIRED"):
        execute("OPENROUTER", "llm", "COMPLETION", {"requests": 1, "tokens": 10, "cost": 0.01, "billable": True},
                lambda: called.append("called"))
    assert called == []
    monkeypatch.setenv("NEXUS_TELEGRAM_RAY_CHAT_IDS", "42")
    with pytest.raises(GovernanceDenied, match="DURABLE_JOB_ID_REQUIRED"):
        from nexus_agent_platform.provider_enforcement import execute_telegram_delivery
        execute_telegram_delivery(42, lambda: called.append("telegram"), job_id="")
    assert called == []


def test_governed_public_read_denies_before_network_without_job_context(monkeypatch):
    from nexus_agent_platform.provider_enforcement import execute_public_read
    monkeypatch.delenv("NEXUS_DURABLE_JOB_ID", raising=False)
    monkeypatch.delenv("NEXUS_CORRELATION_ID", raising=False)
    monkeypatch.delenv("NEXUS_DEPARTMENT", raising=False)
    called = []
    with pytest.raises(GovernanceDenied, match="DURABLE_JOB_ID_REQUIRED"):
        execute_public_read("BROWSER_EXTERNAL_SERVICES", "test_public_read", lambda: called.append("network"))
    assert called == []


def test_shared_http_adapter_denies_unknown_external_hosts_before_network(monkeypatch):
    from alpha import alpha_live_research
    monkeypatch.delenv("NEXUS_DURABLE_JOB_ID", raising=False)
    monkeypatch.setattr(alpha_live_research, "_http_json_unchecked",
                        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network reached")))
    ok, status, _data, error, _latency = alpha_live_research.http_json("GET", "https://unknown.example/api")
    assert not ok and status is None
    assert error == "GOVERNOR_DENIED:DURABLE_JOB_ID_REQUIRED"


def test_standalone_governed_http_requires_job_correlation_and_department_before_socket(monkeypatch):
    from activation.governed_http import get_json
    monkeypatch.delenv("NEXUS_DURABLE_JOB_ID", raising=False)
    monkeypatch.delenv("NEXUS_CORRELATION_ID", raising=False)
    monkeypatch.delenv("NEXUS_DEPARTMENT", raising=False)
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network reached")))
    with pytest.raises(RuntimeError, match="JOB_CORRELATION_DEPARTMENT_REQUIRED"):
        get_json("https://www.googleapis.com/youtube/v3/search", provider="GOOGLE", service="youtube_data_api")


def test_proactive_discovery_public_reads_require_durable_governance(monkeypatch):
    from nexus_agent_platform import proactive_discovery
    monkeypatch.delenv("NEXUS_DURABLE_JOB_ID", raising=False)
    monkeypatch.delenv("NEXUS_CORRELATION_ID", raising=False)
    monkeypatch.delenv("NEXUS_DEPARTMENT", raising=False)
    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network reached")))
    with pytest.raises(GovernanceDenied):
        proactive_discovery._public_json("https://suggestqueries.google.com/complete/search?q=test")


def test_hermes_search_adapter_denies_without_durable_job_before_network(monkeypatch):
    from hermes import hermes_web_search
    monkeypatch.delenv("NEXUS_DURABLE_JOB_ID", raising=False)
    with pytest.raises(GovernanceDenied, match="DURABLE_JOB_ID_REQUIRED"):
        hermes_web_search.governed_urlopen("https://api.search.brave.com/test")


def test_stripe_test_checkout_requires_explicit_ray_approval_and_durable_job(tmp_path, monkeypatch):
    import json
    from approval_lanes import nexus_stripe_test_checkout_lane as lane
    monkeypatch.chdir(tmp_path)
    lane.APPROVAL_DIR = str(tmp_path / "packets")
    packet_dir = tmp_path / "packets"
    packet_dir.mkdir()
    packet = {"item_id":"checkout-test","current_status":"DRAFT","checkout_data":{}}
    (packet_dir / "checkout-test.json").write_text(json.dumps(packet))
    monkeypatch.delenv("NEXUS_DURABLE_JOB_ID", raising=False)
    result = lane.approve_and_create_session("checkout-test")
    assert result["current_status"] == "GOVERNOR_DENIED"
    assert json.loads((packet_dir / "checkout-test.json").read_text())["current_status"] == "GOVERNOR_DENIED"


def test_provider_denial_has_no_execution_and_unrelated_provider_remains_available(tmp_path, monkeypatch):
    path = tmp_path / "gov.sqlite3"
    monkeypatch.setenv("NEXUS_GOVERNOR_DB", str(path))
    monkeypatch.setenv("NEXUS_JOB_BUDGET", '{"max_estimated_cost":1,"max_tokens":100}')
    monkeypatch.setenv("NEXUS_DEPARTMENT", "TEST")
    store = LocalGovernorStore(path)
    store.set_policy("MODAL", "gpu", "RENDER", "DAILY", autonomous_usage_allowed=True,
                     autonomous_spend_allowed=True, hard_limits={"rate": {}, "usage": {"requests": 2}, "money": {"per_day": 0.01}})
    called = []
    with pytest.raises(GovernanceDenied):
        execute("MODAL", "gpu", "GPU_GENERATION", {"requests": 1, "cost": 1, "billable": True},
                lambda: called.append("modal"), job_id="modal-denied", correlation_id="modal-corr", job_type="RENDER")
    assert called == []
    store.set_policy("OPENROUTER", "llm", "ADVISORY", "DAILY", autonomous_usage_allowed=True,
                     autonomous_spend_allowed=True, hard_limits={"rate": {}, "usage": {"tokens": 100}, "money": {"per_day": 1}})
    result = execute("OPENROUTER", "llm", "COMPLETION", {"requests": 1, "tokens": 10, "cost": 0.01, "billable": True},
                     lambda: {"ok": True}, job_id="unrelated-ok", correlation_id="unrelated-corr", job_type="ADVISORY")
    assert result == {"ok": True}


def test_action_classifiers_fail_closed_for_unknown_actions():
    assert classify_browser_action("GET") == "READ_ONLY_BROWSER"
    assert classify_browser_action("BUY") == "PURCHASE_SPEND"
    assert classify_browser_action("chmod_account") == "UNKNOWN_ACTION"
    assert classify_email_action("DRAFT") == "DRAFT"
    assert classify_email_action("BULK_SEND") == "BULK_SEND"
    assert classify_email_action("MASS_FORWARD") == "UNKNOWN_ACTION"
    assert classify_social_action("PUBLIC_POST") == "PUBLIC_POST"
    assert classify_social_action("PAID_PROMOTION") == "PAID_PROMOTION"
    assert classify_social_action("BOOST_MAYBE") == "UNKNOWN_ACTION"


def test_external_action_permissions_fail_closed():
    assert authorize_browser_action("GET") == "READ_ONLY_BROWSER"
    with pytest.raises(GovernanceDenied): authorize_browser_action("CLICK")
    with pytest.raises(GovernanceDenied): authorize_browser_action("BUY", workflow_authorized=True)
    assert authorize_browser_action("BUY", workflow_authorized=True, ray_approved=True, spend_policy_authorized=True) == "PURCHASE_SPEND"
    assert authorize_email_action("DRAFT") == "DRAFT"
    with pytest.raises(GovernanceDenied): authorize_email_action("TEST_SEND")
    assert authorize_email_action("TEST_SEND", approved_test_recipient=True) == "TEST_SEND"
    with pytest.raises(GovernanceDenied): authorize_email_action("BULK_SEND", campaign_approved=True)
    with pytest.raises(GovernanceDenied): authorize_social_action("PUBLIC_POST")
    with pytest.raises(GovernanceDenied): authorize_social_action("PAID_PROMOTION", workflow_authorized=True, ray_approved=True)
    assert authorize_social_action("PAID_PROMOTION", workflow_authorized=True, ray_approved=True,
        spend_policy_authorized=True) == "PAID_PROMOTION"


def test_footprint_redacts_recipient_and_provider_secrets(tmp_path, monkeypatch):
    path = tmp_path / "gov.sqlite3"
    monkeypatch.setenv("NEXUS_GOVERNOR_DB", str(path))
    monkeypatch.setenv("NEXUS_DEPARTMENT", "TEST")
    store = LocalGovernorStore(path)
    store.set_policy("EMAIL_PROVIDER", "resend", "TEST", "DAILY", autonomous_usage_allowed=True,
                     hard_limits={"rate": {}, "usage": {"emails": 4}, "money": {"per_day": 0}})
    execute("EMAIL_PROVIDER", "resend", "TEST_SEND", {"requests": 1, "emails": 1}, lambda: {"id": "mail-ref"},
            job_id="mail-job", correlation_id="mail-corr", job_type="TEST", project_id="project-test", external_ref=lambda result: result["id"])
    with store.connect() as db:
        row=db.execute("SELECT payload,receipt_hash FROM footprints WHERE job_id='mail-job'").fetchone()
        payload = row["payload"]
    assert "mail-ref" in payload
    assert "secret" not in payload.lower() and "credential" not in payload.lower()
    import json
    footprint=json.loads(payload)
    assert footprint["project_id"]=="project-test" and footprint["job_id"]=="mail-job"
    assert all(key in footprint for key in ("correlation_id","department","provider","service","action_type",
        "host","start_time","end_time","request_count","response_bytes","tokens","gpu_seconds",
        "estimated_cost","actual_cost","reservation_amount","final_usage","artifact_refs","handoff_ids",
        "next_job_ids","failure_codes","retry_count","final_state"))
    assert row["receipt_hash"] and len(row["receipt_hash"])==64


def test_provider_failure_containment_matrix_is_job_scoped(tmp_path, monkeypatch):
    path = tmp_path / "gov.sqlite3"
    monkeypatch.setenv("NEXUS_GOVERNOR_DB", str(path))
    monkeypatch.setenv("NEXUS_JOB_BUDGET", '{"max_estimated_cost":10,"max_tokens":100}')
    monkeypatch.setenv("NEXUS_DEPARTMENT", "TEST")
    store = LocalGovernorStore(path)
    store.set_policy("OPENROUTER", "llm", "TOKEN_TEST", "DAILY", autonomous_usage_allowed=True,
        autonomous_spend_allowed=True, hard_limits={"rate": {}, "usage": {"tokens": 10}, "money": {"per_day": 1}})
    no_call = []
    scenarios = [
        ("MODAL", "gpu", "MODAL_TEST", {"requests": 1, "cost": 0.2, "billable": True}),
        ("ORACLE", "resource_creation", "ORACLE_TEST", {"requests": 1, "resource_creations": 1, "cost": 0.2, "billable": True}),
        ("OPENROUTER", "llm", "TOKEN_TEST", {"requests": 1, "tokens": 20, "cost": 0.2, "billable": True}),
    ]
    for i, (provider, service, job_type, estimate) in enumerate(scenarios):
        with pytest.raises(GovernanceDenied):
            execute(provider, service, "CERTIFICATION_FAILURE_CASE", estimate,
                    lambda: no_call.append(i), job_id=f"matrix-{i}", correlation_id=f"matrix-corr-{i}", job_type=job_type)
    with pytest.raises(GovernanceDenied): authorize_browser_action("PUBLICATION")
    with pytest.raises(GovernanceDenied): authorize_email_action("BULK_SEND", campaign_approved=True)
    with pytest.raises(GovernanceDenied): authorize_social_action("PAID_PROMOTION", workflow_authorized=True, ray_approved=True)
    assert no_call == []
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID","matrix-telegram")
    monkeypatch.setenv("NEXUS_TELEGRAM_RAY_CHAT_IDS","42")
    with pytest.raises(GovernanceDenied):
        execute_telegram_delivery("43",lambda:no_call.append("telegram"),job_type="TELEGRAM_TEST")
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID","matrix-email")
    with pytest.raises(GovernanceDenied): authorize_email_action("TEST_SEND",approved_test_recipient=False)
    assert no_call == []
    store.set_policy("OPENROUTER", "llm", "UNRELATED", "DAILY", autonomous_usage_allowed=True,
        autonomous_spend_allowed=True, hard_limits={"rate": {}, "usage": {"tokens": 100}, "money": {"per_day": 1}})
    assert execute("OPENROUTER", "llm", "COMPLETION", {"requests": 1, "tokens": 1, "cost": 0.01, "billable": True},
        lambda: "ok", job_id="matrix-unrelated", correlation_id="matrix-unrelated-corr", job_type="UNRELATED") == "ok"
    with store.connect() as db:
        assert db.execute("SELECT count(*) FROM incidents WHERE job_id GLOB 'matrix-*'").fetchone()[0] >= 5
        assert db.execute("SELECT count(*) FROM footprints WHERE job_id GLOB 'matrix-*'").fetchone()[0] >= 5


def test_telegram_recipient_classification_and_governor_deny(tmp_path, monkeypatch):
    path=tmp_path/"gov.sqlite3";monkeypatch.setenv("NEXUS_GOVERNOR_DB",str(path))
    monkeypatch.setenv("NEXUS_DEPARTMENT", "TEST")
    monkeypatch.setenv("NEXUS_TELEGRAM_RAY_CHAT_IDS","42")
    assert authorize_telegram_action(42)=="RAY_NOTIFICATION"
    with pytest.raises(GovernanceDenied): authorize_telegram_action(-1001)
    store=LocalGovernorStore(path)
    store.set_policy("TELEGRAM","bot_delivery","TELEGRAM_TEST","DAILY",autonomous_usage_allowed=True,
        hard_limits={"rate":{"requests":2,"window_seconds":60},"usage":{"requests":2},"money":{}})
    sent=[]
    result=execute_telegram_delivery(42,lambda:sent.append("sent") or {"result":{"message_id":7}},
        job_id="telegram-test-job",job_type="TELEGRAM_TEST")
    assert result=={"result":{"message_id":7}} and sent==["sent"]
    with pytest.raises(GovernanceDenied):
        execute_telegram_delivery(42,lambda:sent.append("duplicate"),job_id="telegram-test-job",job_type="TELEGRAM_TEST")
    assert sent==["sent"]


def test_temporal_delivery_activities_deny_without_authority_before_network(tmp_path,monkeypatch):
    import asyncio
    from nexus_agent_platform.workflows import temporal_activities
    path=tmp_path/"gov.sqlite3"
    monkeypatch.setenv("NEXUS_GOVERNOR_DB",str(path))
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN","test-token")
    monkeypatch.setenv("TELEGRAM_ALLOWED_CHAT_IDS","42")
    monkeypatch.setenv("SUPABASE_URL","https://example.invalid")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY","not-used")
    monkeypatch.delenv("NEXUS_TELEGRAM_RAY_CHAT_IDS",raising=False)
    monkeypatch.delenv("NEXUS_TELEGRAM_INTERNAL_CHAT_IDS",raising=False)
    monkeypatch.delenv("NEXUS_TEMPORAL_EMAIL_WORKFLOW_AUTHORIZED",raising=False)
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID","temporal-telegram-test")
    with pytest.raises(GovernanceDenied):
        asyncio.run(temporal_activities.deliver_telegram_report_activity("42","mock report"))
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID","temporal-email-test")
    with pytest.raises(GovernanceDenied):
        asyncio.run(temporal_activities.send_email_activity("ray@example.invalid","subject","body","temporal-mail-job"))
    with LocalGovernorStore(path).connect() as db:
        assert db.execute("SELECT count(*) FROM incidents").fetchone()[0]==2
        assert db.execute("SELECT count(*) FROM footprints").fetchone()[0]==2
