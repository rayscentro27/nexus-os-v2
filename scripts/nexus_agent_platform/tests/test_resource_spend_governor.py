from __future__ import annotations

import threading
import asyncio
from pathlib import Path

import pytest

from nexus_agent_platform.resource_spend_governor import GovernanceDenied, LocalGovernorStore


def store_at(path: Path) -> LocalGovernorStore:
    return LocalGovernorStore(path / "governor.sqlite3")


def limits(*, requests=0, bytes_=0, tokens=0, cost_job=0, cost_day=0):
    return {"rate":{"requests":requests,"operations":0,"window_seconds":60},
            "usage":{"bytes":bytes_,"tokens":tokens},
            "money":{"per_job":cost_job,"per_day":cost_day,"per_month":cost_day*10}}


def authorize_test(store, provider, job, estimate, purpose="test"):
    return store.reserve(provider,"cert","MOCK",job,estimate,purpose=purpose)


def test_unknown_provider_and_credentials_default_deny(tmp_path):
    store=store_at(tmp_path)
    with pytest.raises(GovernanceDenied,match="UNKNOWN_PAID_PROVIDER"):
        authorize_test(store,"CREDENTIALS_EXISTENCE_IS_NOT_AUTHORITY","job-a",{"cost":0.01,"billable":True})
    with pytest.raises(GovernanceDenied,match="USAGE_NOT_AUTHORIZED"):
        authorize_test(store,"OPENROUTER","job-b",{"requests":1,"cost":0,"billable":False})
    assert store.summary()["active_reservations"]==0


@pytest.mark.parametrize("estimate,hard,code",[
    ({"requests":2,"cost":0},{"rate":{"requests":1,"window_seconds":60}},"RATE_LIMIT"),
    ({"bytes":101,"cost":0},{"usage":{"bytes":100}},"BUDGET_HARD_LIMIT"),
    ({"tokens":1001,"cost":0},{"usage":{"tokens":1000}},"BUDGET_HARD_LIMIT"),
    ({"cost":2,"billable":True},{"money":{"per_job":1,"per_day":5}},"JOB_COST_LIMIT"),
])
def test_separate_hard_budget_dimensions_block_before_reservation(tmp_path,estimate,hard,code,monkeypatch):
    if estimate.get("cost"): monkeypatch.setenv("NEXUS_JOB_BUDGET",'{"max_estimated_cost":10}')
    store=store_at(tmp_path); base=limits()
    for key,value in hard.items(): base[key].update(value)
    store.set_policy("OPENROUTER","cert","MOCK","DAILY",autonomous_usage_allowed=True,autonomous_spend_allowed=True,hard_limits=base)
    with pytest.raises(GovernanceDenied,match=code): authorize_test(store,"OPENROUTER","job-a",estimate)
    assert store.summary()["active_reservations"]==0


def test_atomic_budget_reservation_allows_only_one_competing_job(tmp_path,monkeypatch):
    monkeypatch.setenv("NEXUS_JOB_BUDGET",'{"max_estimated_cost":10}')
    store=store_at(tmp_path)
    store.set_policy("MODAL","cert","MOCK","DAILY",autonomous_usage_allowed=True,autonomous_spend_allowed=True,
                     hard_limits=limits(cost_job=10,cost_day=10),concurrency_limit=2)
    barrier=threading.Barrier(2); outcomes=[]
    def attempt(job):
        barrier.wait()
        try: outcomes.append((job,authorize_test(store,"MODAL",job,{"cost":6,"billable":True})))
        except GovernanceDenied as exc: outcomes.append((job,exc.code))
    threads=[threading.Thread(target=attempt,args=(f"job-{i}",)) for i in range(2)]
    [thread.start() for thread in threads]; [thread.join() for thread in threads]
    assert sum(isinstance(value,dict) for _,value in outcomes)==1
    assert store.summary()["active_reservations"]==1


def test_durable_worker_envelope_reserves_each_bounded_attempt(tmp_path):
    store=store_at(tmp_path)
    store.set_policy("SUPABASE","durable_worker","*","DAILY",autonomous_usage_allowed=True,
                     hard_limits={**limits(requests=300,bytes_=50_000_000),"usage":{"requests":120,"bytes":2_000_000},"rate":{"requests":300,"operations":300,"window_seconds":60}})
    first=store.reserve("SUPABASE","durable_worker","CREATIVE_BRIEF_BUILD","job-retry",
                        {"requests":120,"bytes":2_000_000,"cost":0},purpose="durable-job-envelope:attempt-1")
    store.reconcile(first["reservation_id"],{"requests":4,"bytes":512,"cost":0})
    retry=store.reserve("SUPABASE","durable_worker","CREATIVE_BRIEF_BUILD","job-retry",
                        {"requests":116,"bytes":1_999_488,"cost":0},purpose="durable-job-envelope:attempt-2")
    assert retry["status"]=="ACTIVE"


def test_provider_hard_stop_does_not_block_unrelated_provider(tmp_path,monkeypatch):
    monkeypatch.setenv("NEXUS_JOB_BUDGET",'{"max_estimated_cost":10}')
    store=store_at(tmp_path)
    store.set_policy("FAL_AI","cert","MOCK","DAILY",autonomous_usage_allowed=True,autonomous_spend_allowed=True,
                     hard_limits=limits(cost_job=1,cost_day=2))
    with pytest.raises(GovernanceDenied,match="JOB_COST_LIMIT"):
        authorize_test(store,"FAL_AI","provider-a-job",{"cost":2,"billable":True})
    store.set_policy("SUPABASE","cert","MOCK","DAILY",autonomous_usage_allowed=True,autonomous_spend_allowed=False,
                     hard_limits=limits(requests=10,bytes_=1000))
    reservation=authorize_test(store,"SUPABASE","provider-b-job",{"requests":1,"bytes":20,"cost":0})
    assert reservation["status"]=="ACTIVE"


def test_resource_creation_retry_is_idempotent_and_bounded(tmp_path,monkeypatch):
    monkeypatch.setenv("NEXUS_JOB_BUDGET",'{"max_resource_creations":1}')
    store=store_at(tmp_path)
    store.set_policy("ORACLE","resource_creation","GOVERNOR_CERT","DAILY",autonomous_usage_allowed=True,autonomous_spend_allowed=True,resource_creation_limit=1)
    first=store.resource_create("job-1","ORACLE","research-worker",job_type="GOVERNOR_CERT",max_per_job=1,max_per_day=1)
    retry=store.resource_create("job-1","ORACLE","research-worker",job_type="GOVERNOR_CERT",max_per_job=1,max_per_day=1)
    assert first==retry
    with pytest.raises(GovernanceDenied,match="RESOURCE_CREATION_LIMIT"):
        store.resource_create("job-1","ORACLE","second-worker",job_type="GOVERNOR_CERT",max_per_job=1,max_per_day=1)


def test_footprint_redacts_sensitive_fields_and_certification_ledger(tmp_path):
    store=store_at(tmp_path)
    receipt=store.record_footprint({"job_id":"job-1","correlation_id":"corr-1","department":"RESEARCH","job_type":"MOCK","token":"must-not-persist","transcript":"private"})
    with store.connect() as db:
        row=db.execute("select payload,receipt_hash from footprints where job_id='job-1'").fetchone()
        assert "must-not-persist" not in row["payload"] and "private" not in row["payload"]
        assert row["receipt_hash"]==receipt
    store.certify("governor-local","MOCK_PASS",project_id="NEXUS",job_id="job-1",host="local")
    with store.connect() as db: assert db.execute("select status from certifications").fetchone()[0]=="MOCK_PASS"


def test_llm_adapter_denies_before_network_even_when_credential_is_present(tmp_path,monkeypatch):
    monkeypatch.setenv("NEXUS_GOVERNOR_DB",str(tmp_path/"governor.sqlite3"))
    monkeypatch.setenv("OPENROUTER_API_KEY","credential-presence-is-not-authority")
    from nexus_agent_platform.workflows.litellm_adapter import LlmGatewayAdapter
    adapter=LlmGatewayAdapter("governor-cert")
    async def should_not_call(*args,**kwargs): raise AssertionError("provider call must be denied before network")
    monkeypatch.setattr(adapter,"_fallback_completion",should_not_call)
    result=asyncio.run(adapter.completion("openai/gpt-4o-mini",[{"role":"user","content":"mock"}]))
    assert result["error"]=="GOVERNANCE_DENIED"
    assert result["governor_state"]=="HUMAN_APPROVAL_REQUIRED"
