from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts/research"))

from nexus_agent_platform.resource_spend_governor import (
    GovernanceDenied, LocalGovernorStore, default_store,
)


def _limits():
    return {"rate": {"requests": 6, "operations": 6, "window_seconds": 60},
            "usage": {"bytes": 500000, "runtime_seconds": 900, "cost": 0},
            "money": {"per_job": 0, "per_day": 0, "per_month": 0}}


def test_scoped_policy_resolves_before_disabled_wildcard(tmp_path):
    store = LocalGovernorStore(tmp_path / "governor.sqlite3")
    assert store.ensure_policy("NOTEBOOKLM", "research_discovery", "NEXUS_RESEARCH_NOTEBOOKLM", "DAILY",
        autonomous_usage_allowed=True, autonomous_spend_allowed=False,
        soft_limits=_limits(), hard_limits=_limits(), concurrency_limit=1,
        resource_creation_limit=0, state="NORMAL", approval_required=False)
    resolved = store.resolve_policy("NOTEBOOKLM", "research_discovery", "NEXUS_RESEARCH_NOTEBOOKLM")
    assert resolved["state"] == "NORMAL"
    assert resolved["service"] == "research_discovery"
    assert resolved["job_type"] == "NEXUS_RESEARCH_NOTEBOOKLM"
    assert resolved["wildcard_fallback_used"] is False


def test_insert_only_scoped_policy_does_not_reopen_stop(tmp_path):
    store = LocalGovernorStore(tmp_path / "governor.sqlite3")
    store.set_policy("NOTEBOOKLM", "research_discovery", "NEXUS_RESEARCH_NOTEBOOKLM", "DAILY",
        autonomous_usage_allowed=False, autonomous_spend_allowed=False,
        soft_limits=_limits(), hard_limits=_limits(), state="HARD_STOP", approval_required=True)
    assert not store.ensure_policy("NOTEBOOKLM", "research_discovery", "NEXUS_RESEARCH_NOTEBOOKLM", "DAILY",
        autonomous_usage_allowed=True, autonomous_spend_allowed=False,
        soft_limits=_limits(), hard_limits=_limits(), state="NORMAL", approval_required=False)
    assert store.resolve_policy("NOTEBOOKLM", "research_discovery", "NEXUS_RESEARCH_NOTEBOOKLM")["state"] == "HARD_STOP"


def test_research_policy_initializer_preserves_existing_hard_stop(tmp_path, monkeypatch):
    from research import notebooklm_research_adapter as adapter_module
    db_path=tmp_path/"governor.sqlite3"
    monkeypatch.setenv("NEXUS_GOVERNOR_DB",str(db_path))
    monkeypatch.setattr(adapter_module,"_RESEARCH_POLICY_READY",False)
    store=LocalGovernorStore(db_path)
    for period in ("DAILY","MONTHLY"):
        store.set_policy("NOTEBOOKLM","research_discovery","NEXUS_RESEARCH_NOTEBOOKLM",period,
            autonomous_usage_allowed=True,autonomous_spend_allowed=False,
            soft_limits=_limits(),hard_limits=_limits(),state="HARD_STOP",approval_required=False)
        store.set_policy("SUPABASE","durable_worker","*",period,
            autonomous_usage_allowed=True,autonomous_spend_allowed=False,
            soft_limits={"rate":{"requests":10,"operations":10,"window_seconds":60},
                         "usage":{"requests":5000,"bytes":5000000,"cost":0}},
            hard_limits={"rate":{"requests":10,"operations":10,"window_seconds":60},
                         "usage":{"requests":5000,"bytes":5000000,"cost":0}},
            concurrency_limit=2,state="NORMAL",approval_required=False)
    adapter_module._ensure_research_notebooklm_policy()
    assert store.resolve_policy("NOTEBOOKLM","research_discovery","NEXUS_RESEARCH_NOTEBOOKLM","DAILY")["state"]=="HARD_STOP"
    assert store.resolve_policy("NOTEBOOKLM","research_discovery","NEXUS_RESEARCH_NOTEBOOKLM","MONTHLY")["state"]=="HARD_STOP"


def test_unrelated_resource_stays_denied(tmp_path):
    store = LocalGovernorStore(tmp_path / "governor.sqlite3")
    with pytest.raises(GovernanceDenied):
        store.reserve("NOTEBOOKLM", "arbitrary_shell", "NEXUS_RESEARCH_NOTEBOOKLM", "job-1",
                      {"requests": 1, "bytes": 1, "cost": 0})


def test_single_job_canary_policy_is_scoped_and_metered_without_changing_legacy_cap(tmp_path):
    from nexus_agent_platform.notebooklm_discovery import (
        DEDICATED_CANARY_CASE_ID, DEDICATED_CANARY_JOB_ID,
        DEDICATED_CANARY_POLICY_JOB_TYPE, ensure_dedicated_canary_policy,
    )
    store = LocalGovernorStore(tmp_path / "governor.sqlite3")
    store.set_policy("NOTEBOOKLM", "research_discovery", "NEXUS_RESEARCH_NOTEBOOKLM", "DAILY",
        autonomous_usage_allowed=True, autonomous_spend_allowed=False,
        soft_limits=_limits(), hard_limits=_limits(), state="HARD_STOP", approval_required=False)
    resolved = ensure_dedicated_canary_policy(store, job_id=DEDICATED_CANARY_JOB_ID,
                                               case_id=DEDICATED_CANARY_CASE_ID)
    assert resolved["DAILY"]["job_type"] == DEDICATED_CANARY_POLICY_JOB_TYPE
    assert resolved["DAILY"]["wildcard_fallback_used"] is False
    assert resolved["DAILY"]["state"] == "NORMAL"
    assert resolved["DAILY"]["autonomous_spend_allowed"] is False
    limits = resolved["DAILY"]["hard_limits"]
    if isinstance(limits, str):
        limits = json.loads(limits)
    assert limits["usage"]["bytes"] == 1_200_000
    legacy = store.resolve_policy("NOTEBOOKLM", "research_discovery", "NEXUS_RESEARCH_NOTEBOOKLM", "DAILY")
    assert legacy["state"] == "HARD_STOP"
    legacy_limits = legacy["hard_limits"]
    if isinstance(legacy_limits, str):
        legacy_limits = json.loads(legacy_limits)
    assert legacy_limits["usage"]["bytes"] == 500_000


def test_canary_policy_cannot_be_reused_by_another_job_or_case(tmp_path):
    from nexus_agent_platform.notebooklm_discovery import ensure_dedicated_canary_policy
    store = LocalGovernorStore(tmp_path / "governor.sqlite3")
    with pytest.raises(PermissionError, match="DEDICATED_CANARY_SCOPE_NOT_AUTHORIZED"):
        ensure_dedicated_canary_policy(store, job_id="another-job", case_id="another-case")
    assert store.resolve_policy("NOTEBOOKLM", "research_discovery", "*") is None


def test_full_research_canary_policy_is_job_scoped_bounded_and_zero_spend(tmp_path):
    from nexus_agent_platform.notebooklm_discovery import (
        FULL_RESEARCH_CANARY_LIMITS, ensure_full_research_canary_policy,
        full_research_canary_policy_job_type,
    )
    store=LocalGovernorStore(tmp_path/"governor.sqlite3")
    store.set_policy("NOTEBOOKLM","research_discovery","NEXUS_RESEARCH_NOTEBOOKLM","DAILY",
        autonomous_usage_allowed=False,autonomous_spend_allowed=False,soft_limits=_limits(),
        hard_limits=_limits(),state="HARD_STOP",approval_required=False)
    job_id="job_"+"a"*32
    case_id="nexus_full_research_canary_20261012_test"
    result=ensure_full_research_canary_policy(store,job_id=job_id,case_id=case_id)
    assert result["DAILY"]["job_type"]==full_research_canary_policy_job_type(job_id)
    assert result["DAILY"]["state"]=="NORMAL"
    assert result["DAILY"]["autonomous_spend_allowed"] is False
    assert result["DAILY"]["wildcard_fallback_used"] is False
    limits=result["DAILY"]["hard_limits"]
    if isinstance(limits,str): limits=json.loads(limits)
    assert limits["usage"]["bytes"]==4_000_000
    assert FULL_RESEARCH_CANARY_LIMITS["money"]["per_job"]==0
    assert store.resolve_policy("NOTEBOOKLM","research_discovery","NEXUS_RESEARCH_NOTEBOOKLM","DAILY")["state"]=="HARD_STOP"


def test_full_research_canary_policy_does_not_reopen_its_own_hard_stop(tmp_path):
    from nexus_agent_platform.notebooklm_discovery import full_research_canary_policy_job_type,ensure_full_research_canary_policy
    store=LocalGovernorStore(tmp_path/"governor.sqlite3")
    job_id="job_"+"b"*32; case_id="nexus_full_research_canary_test"
    kind=full_research_canary_policy_job_type(job_id)
    store.set_policy("NOTEBOOKLM","research_discovery",kind,"DAILY",autonomous_usage_allowed=False,
        autonomous_spend_allowed=False,soft_limits=_limits(),hard_limits=_limits(),state="HARD_STOP",approval_required=True)
    with pytest.raises(RuntimeError,match="POLICY_NOT_NORMAL"):
        ensure_full_research_canary_policy(store,job_id=job_id,case_id=case_id)
    assert store.resolve_policy("NOTEBOOKLM","research_discovery",kind,"DAILY")["state"]=="HARD_STOP"


def test_recovered_notebook_source_requires_multiple_subject_terms():
    from nexus_agent_platform.notebooklm_discovery import _source_matches_research_subject

    subject="Custom AI Agents for Restaurant Owners"
    assert _source_matches_research_subject(subject, {
        "title":"AI Voice Agent for Restaurants: Orders, Bookings 24/7",
        "url":"https://example.com/restaurant-voice-agent",
    })
    assert _source_matches_research_subject(subject, {
        "title":"AI in Restaurants: Use Cases, Costs, ROI & Steps",
        "url":"https://example.com/ai-in-restaurants",
    })
    assert not _source_matches_research_subject(subject, {
        "title":"Restaurant Industry Overview",
        "url":"https://example.com/restaurants",
    })


def test_dedicated_canary_handler_rejects_unrelated_case_before_provider_calls():
    from types import SimpleNamespace
    from nexus_agent_platform.notebooklm_discovery import execute_dedicated_research_canary
    job = SimpleNamespace(job_id="job_bd4b15de2c051b08e0b041582437892d")
    result = execute_dedicated_research_canary(job, {
        "case_id": "not-the-authorized-canary",
        "source_url": "https://www.youtube.com/watch?v=GumqxlRHoHk",
        "source_title": "Public source",
        "feeder_notebook_id": "e0657f43-bf4e-4241-8336-7854739e942d",
        "feeder_source_id": "82c48caa-0403-4bcb-a2d1-8680a154b0d7",
        "research_subject": "Custom AI Agents for Restaurant Owners",
    })
    assert result == {"status": "BLOCKED", "reason": "DEDICATED_CANARY_SCOPE_NOT_AUTHORIZED"}


def test_stopped_canary_scope_is_not_reopened(tmp_path):
    from nexus_agent_platform.notebooklm_discovery import (
        DEDICATED_CANARY_CASE_ID, DEDICATED_CANARY_JOB_ID,
        DEDICATED_CANARY_POLICY_JOB_TYPE, DEDICATED_CANARY_LIMITS,
        ensure_dedicated_canary_policy,
    )
    store = LocalGovernorStore(tmp_path / "governor.sqlite3")
    store.set_policy("NOTEBOOKLM", "research_discovery", DEDICATED_CANARY_POLICY_JOB_TYPE, "DAILY",
        autonomous_usage_allowed=False, autonomous_spend_allowed=False,
        soft_limits=DEDICATED_CANARY_LIMITS, hard_limits=DEDICATED_CANARY_LIMITS,
        state="HARD_STOP", approval_required=True)
    with pytest.raises(RuntimeError, match="CANARY_POLICY_NOT_NORMAL:DAILY:HARD_STOP"):
        ensure_dedicated_canary_policy(store, job_id=DEDICATED_CANARY_JOB_ID,
                                       case_id=DEDICATED_CANARY_CASE_ID)
    assert store.resolve_policy("NOTEBOOKLM", "research_discovery", DEDICATED_CANARY_POLICY_JOB_TYPE,
                                "DAILY")["state"] == "HARD_STOP"


def test_canary_answer_improvement_requires_new_cited_evidence_not_length():
    from nexus_agent_platform.notebooklm_discovery import classify_canary_answer_improvement
    source_id = "web-source-1"
    assert classify_canary_answer_improvement("short", "a much longer answer without evidence " * 100,
        new_source_ids={source_id}, answer_source_ids={source_id}) == "NO"
    assert classify_canary_answer_improvement("No data found.", "Report states 48% plan to raise tech spending [2].",
        new_source_ids={source_id}, answer_source_ids={source_id}) == "YES"
    assert classify_canary_answer_improvement("No data found.", "Partially verified with new source [2].",
        new_source_ids={source_id}, answer_source_ids={source_id}) == "PARTIAL"


def test_research_adapter_cli_uses_scoped_governor_and_compact_accounting(tmp_path, monkeypatch):
    from research import notebooklm_research_adapter as adapter_module

    db_path = tmp_path / "governor.sqlite3"
    monkeypatch.setenv("NEXUS_GOVERNOR_DB", str(db_path))
    monkeypatch.setenv("NEXUS_DURABLE_JOB_ID", "research-canary-job")
    monkeypatch.setenv("NEXUS_CORRELATION_ID", "research-canary-correlation")
    monkeypatch.setenv("NEXUS_DEPARTMENT", "RESEARCH")
    monkeypatch.setenv("NEXUS_JOB_TYPE", "RESEARCH_GAP_VERIFY")
    monkeypatch.setattr(adapter_module, "_RESEARCH_POLICY_READY", False)
    local = LocalGovernorStore(db_path)
    for period in ("DAILY", "MONTHLY"):
        local.set_policy("SUPABASE", "durable_worker", "*", period,
            autonomous_usage_allowed=True, autonomous_spend_allowed=False,
            soft_limits={"rate":{"requests":10,"operations":10,"window_seconds":60},
                         "usage":{"requests":5000,"bytes":5000000,"cost":0}},
            hard_limits={"rate":{"requests":10,"operations":10,"window_seconds":60},
                         "usage":{"requests":5000,"bytes":5000000,"cost":0}},
            concurrency_limit=2, state="NORMAL", approval_required=False)

    def fake_run(*_args, **_kwargs):
        return __import__("subprocess").CompletedProcess([], 0, stdout='{"ok":true}', stderr="")

    monkeypatch.setattr(adapter_module.subprocess, "run", fake_run)
    adapter=adapter_module.NotebookLMResearchAdapter()
    result = adapter._run_json(["list", "--json"], stage="list")
    repeated = adapter._run_json(["list", "--json"], stage="list")
    assert result == {"ok": True}
    assert repeated == result

    store = default_store()
    policy = store.resolve_policy("NOTEBOOKLM", "research_discovery", "NEXUS_RESEARCH_NOTEBOOKLM", "DAILY")
    assert policy["state"] == "NORMAL"
    assert policy["wildcard_fallback_used"] is False
    assert policy["autonomous_spend_allowed"] is False
    with store.connect() as db:
        rows = db.execute("SELECT idempotency_key,estimate,actual FROM reservations WHERE job_id=?", ("research-canary-job",)).fetchall()
        assert len(rows) == 2
        assert rows[0][0] != rows[1][0]
        assert "list" not in rows[0]["estimate"]
        assert "ok" not in rows[0]["actual"]
        footprints = [json.loads(row[0]) for row in db.execute("SELECT payload FROM footprints WHERE job_id=?", ("research-canary-job",))]
    assert footprints
    encoded = json.dumps(footprints)
    assert '"--json"' not in encoded
    assert '{\\"ok\\":true}' not in encoded


def test_research_adapter_fails_closed_without_durable_context(monkeypatch):
    from research import notebooklm_research_adapter as adapter_module
    monkeypatch.setenv("NEXUS_DEPARTMENT", "RESEARCH")
    monkeypatch.delenv("NEXUS_DURABLE_JOB_ID", raising=False)
    monkeypatch.delenv("NEXUS_CORRELATION_ID", raising=False)
    with pytest.raises(GovernanceDenied, match="DURABLE_RESEARCH_CONTEXT_REQUIRED"):
        adapter_module.NotebookLMResearchAdapter()._run(["list", "--json"], stage="list")


def test_research_case_lookup_uses_exact_id_not_full_case_scan(tmp_path, monkeypatch):
    from research import research_case_engine as cases
    expected = {"case_id": "case-123", "memory_kind": "RESEARCH_CASE", "notebook_id": "nb-1"}
    calls = []
    monkeypatch.setattr(cases.research_memory, "hydrate_memory",
        lambda memory_id: calls.append(memory_id) or expected)
    empty=tmp_path / "research_runtime_states.jsonl"
    empty.write_text("")
    monkeypatch.setattr(cases.persistence,"collection_path",lambda _collection:empty)
    monkeypatch.setattr(cases, "_latest_cases",
        lambda: (_ for _ in ()).throw(AssertionError("broad case hydration is forbidden")))
    assert cases.get_case("case-123") == expected
    assert calls == ["case-123"]


def test_research_case_lookup_falls_back_to_local_exact_id(tmp_path, monkeypatch):
    from research import research_case_engine as cases
    local_file=tmp_path / "research_runtime_states.jsonl"
    monkeypatch.setattr(cases.research_memory, "hydrate_memory", lambda _memory_id: None)
    local_file.write_text("\n".join(json.dumps(row) for row in [
        {"case_id":"other", "memory_kind":"RESEARCH_CASE", "recorded_at":"2026-01-01"},
        {"case_id":"case-123", "memory_kind":"RESEARCH_CASE", "recorded_at":"2026-01-01", "state":1},
        {"case_id":"case-123", "memory_kind":"RESEARCH_CASE", "recorded_at":"2026-01-02", "state":2},
    ])+"\n")
    monkeypatch.setattr(cases.persistence,"collection_path",lambda _collection:local_file)
    assert cases.get_case("case-123")["state"] == 2


def test_research_case_lookup_prefers_newer_local_checkpoint_over_remote(tmp_path, monkeypatch):
    from research import research_case_engine as cases
    local_file=tmp_path / "research_runtime_states.jsonl"
    local_file.write_text(json.dumps({"case_id":"case-123", "memory_kind":"RESEARCH_CASE",
        "recorded_at":"2026-01-02", "state":"local-newer"})+"\n")
    monkeypatch.setattr(cases.research_memory, "hydrate_memory", lambda _memory_id: {
        "case_id":"case-123", "memory_kind":"RESEARCH_CASE", "recorded_at":"2026-01-01", "state":"remote"})
    monkeypatch.setattr(cases.persistence,"collection_path",lambda _collection:local_file)
    assert cases.get_case("case-123")["state"] == "local-newer"


def test_bounded_canary_reuses_notebook_and_queues_existing_needle_flow(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from nexus_agent_platform import notebooklm_discovery as discovery
    from research import notebook_completion_contracts as contracts

    case_id = "nexus_runtime_canary_be0b211fba5"
    notebook_id = "053dbdf7-089b-45f9-a1d8-8540ed19c289"
    source_id = "source-existing-canary"
    bound = {}

    class FakeAdapter:
        @staticmethod
        def video_id_of(url):
            return url.rsplit("/", 1)[-1]
        def __init__(self, *_args, **_kwargs):
            pass
        def notebooks(self, **_kwargs):
            return [{"id":notebook_id,"title":f"Nexus Research Case {case_id}"}]
        def sources(self, _notebook_id, **_kwargs):
            return [{"id":source_id,"title":"Official pricing", "url":"https://example.test/pricing"}]
        def find_existing_source(self, rows, **_kwargs):
            return rows[0]
        def add_source(self, *_args, **_kwargs):
            raise AssertionError("reused source should not be added")
        def wait_for_source(self, *_args, **_kwargs):
            return {"status":"ready"}
        def ask_source_scoped(self, *_args, **_kwargs):
            return {"answer":"A bounded canary answer", "response_reference":"turn-1"}
        def verify_visible_turn(self, *_args, **_kwargs):
            return True

    monkeypatch.setattr(discovery, "ROOT", tmp_path)
    monkeypatch.setattr(discovery, "execute", lambda *args, **_kwargs: args[4]())
    monkeypatch.setattr("research.notebooklm_research_adapter._ensure_research_notebooklm_policy", lambda: None)
    monkeypatch.setattr("research.notebooklm_research_adapter.NotebookLMResearchAdapter", FakeAdapter)
    monkeypatch.setattr("research.research_case_engine.bind_notebook_workspace",
                        lambda selected, notebook: bound.update({"case_id":selected,"notebook_id":notebook["notebook_id"]}))
    monkeypatch.setattr("research.research_case_engine.add_source", lambda *_a, **_k: {"ok":True})
    contract = {"contract_id":"BUSINESS_OPPORTUNITY_MISSION_NOTEBOOK_V1","research_purpose":"MISSION_RESEARCH",
        "research_domain":"BUSINESS_OPPORTUNITY","notebook_id":notebook_id,"verification_status":"NEEDLE_VERIFICATION_QUEUED",
        "required_questions":[{"required":True,"asked":True}],"handoff_package":{"schema":"compact"}}
    monkeypatch.setattr(contracts, "load_state", lambda **_k: contract)
    monkeypatch.setattr("research.research_case_engine.get_case", lambda _case_id: {
        "case_id":case_id,"objective":"Bounded pricing evidence test","research_purpose":None,
        "research_domain":None,"objective_family":""})
    classifications = []
    monkeypatch.setattr("research.research_case_engine._save",
        lambda _case, event, **details: classifications.append((event, details)) or {**_case, **details})
    monkeypatch.setattr("research.notebook_playbook_runner.run_case_playbook", lambda selected, **_k: {
        "ok":False,"receipt_id":"research-receipt","needle_job":{"job_id":"needle-live-id"},
        "verification":{"complete":True}})
    job = SimpleNamespace(job_id="research-live-id", correlation_id="corr-live", attempt_count=1)
    result = discovery.execute_runtime_canary(job, {"case_id":case_id,
        "source_url":"https://example.test/pricing","source_title":"Official pricing",
        "question":"Summarize the pricing shown.","reuse_existing_notebook_only":True,
        "run_completion_contract":True,"research_purpose":"MISSION_RESEARCH",
        "research_domain":"BUSINESS_OPPORTUNITY"})
    assert result["status"] == "COMPLETED", result
    assert result["notebook_id"] == notebook_id
    assert result["completion_contract"]["needle_job_id"] == "needle-live-id"
    assert result["completion_contract"]["research_receipt_id"] == "research-receipt"
    assert bound == {"case_id":case_id,"notebook_id":notebook_id}
    assert classifications[0][0] == "RESEARCH_CONTRACT_CLASSIFIED"
    assert classifications[0][1]["notebook_contract_id"] == "BUSINESS_OPPORTUNITY_MISSION_NOTEBOOK_V1"
    assert "A bounded canary answer" not in json.dumps(result)
    assert result["completion_contract"]["no_full_notebook_mirror_to_supabase"] is True


def test_completion_contract_retry_does_not_repeat_confirmed_question_prompt(monkeypatch):
    from contextlib import nullcontext
    from research import notebook_completion_contracts as contracts
    from research import notebook_playbook_runner as runner

    state=contracts.new_contract_state(objective="Bounded process canary",
        research_purpose="MISSION_RESEARCH",research_domain="BUSINESS_OPPORTUNITY",
        notebook_id="notebook-canary-id",research_job_id="job-canary")
    prompt=contracts.build_required_question_prompt(state)
    contracts.register_notebook_submission(state,prompt=prompt,submission_confirmed=True,
        response=json.dumps({"question_results":[{"question_id":q["question_id"],"evidence_status":"UNVERIFIED"}
            for q in state["required_questions"]]}))
    contracts.record_gap_review(state,question_ids=[q["question_id"] for q in state["required_questions"][:3]],
        supplementation_attempted=True,unresolved_note="Bounded source check completed; unresolved details remain.")
    asked=[]
    class FakeAdapter:
        def _job_slot(self): return nullcontext()
        def resolve_case_notebook(self,*_a,**_k): return {"notebook_id":"notebook-canary-id","title":"canary"}
        def sources(self,_notebook_id): return [{"id":"source-1"}]
        def ask_notebook(self,_notebook_id,question):
            asked.append(question)
            selected=contracts.select_contract("MISSION_RESEARCH","BUSINESS_OPPORTUNITY")
            answer={"synthesis":"Bounded evidence remains mostly unverified.",
                "action_statement":{field:"explicitly unknown or bounded" for field in selected["action_fields"]},
                "structured_extraction":{"evidence_status":"UNVERIFIED"}}
            return {"answer":json.dumps(answer),"references":[],"submission_confirmed":True}

    case={"case_id":"case-canary","objective":"Bounded process canary",
        "research_purpose":"MISSION_RESEARCH","research_domain":"BUSINESS_OPPORTUNITY",
        "sources":[{"source_id":"source-1","notebook_id":"notebook-canary-id"}],
        "notebook_workspace":{"notebook_id":"notebook-canary-id"}}
    monkeypatch.setattr(runner.cases,"get_case",lambda _case_id:case)
    monkeypatch.setattr(runner.cases,"bind_notebook_workspace",lambda *_a,**_k:{"ok":True})
    monkeypatch.setattr(runner.cases,"record_notebook_answer",lambda *_a,**_k:{"ok":True})
    monkeypatch.setattr(runner.cases,"_save",lambda current,_event,**details:{**current,**details})
    monkeypatch.setattr(runner,"load_completion_state",lambda **_k:state)
    monkeypatch.setattr(runner,"persist_completion_state",lambda *_a,**_k:"local-contract.json")
    monkeypatch.setattr(runner,"expand_case_from_best_gap",lambda *_a,**_k:{"ok":True,"added_sources":[]})
    monkeypatch.setattr(runner,"_record",lambda _row:None)
    result=runner.run_case_playbook("case-canary",adapter=FakeAdapter(),source_work_id="job-canary",
        adaptive_director=False)
    assert result["ok"] is False  # remaining gaps stay visible; no false completion
    assert len(asked)==1 and "Synthesize the completed research objective" in asked[0]
    assert "REQUIRED QUESTIONS:" not in asked[0]  # only the final synthesis runs


def test_research_reuses_hash_verified_local_synthesis_after_worker_restart(tmp_path, monkeypatch):
    import hashlib
    from research import notebook_playbook_runner as runner
    answer="```json\n"+json.dumps({"synthesis":"persisted","action_statement":{},
        "structured_extraction":{}})+"\n```"
    ref="data/runtime/notebook_answer_artifacts/case-1/answer.json"
    target=tmp_path / ref
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps({"answer":answer}))
    monkeypatch.setattr(runner,"ROOT",tmp_path)
    case={"notebook_answers":[{"question_type":"CONTRACT_SYNTHESIS:BUSINESS_OPPORTUNITY_MISSION_NOTEBOOK_V1",
        "notebook_id":"nb-1","response_persisted":True,"response_hash":hashlib.sha256(answer.encode()).hexdigest(),
        "local_artifact_ref":ref,"source_ids":["source-1"],"response_reference":"turn-1"}]}
    result=runner._load_persisted_notebook_answer(case,
        question_type="CONTRACT_SYNTHESIS:BUSINESS_OPPORTUNITY_MISSION_NOTEBOOK_V1",notebook_id="nb-1")
    assert result and result["answer"]==answer and result["source_ids"]==["source-1"]
    case["notebook_answers"][0]["response_hash"]="wrong"
    assert runner._load_persisted_notebook_answer(case,
        question_type="CONTRACT_SYNTHESIS:BUSINESS_OPPORTUNITY_MISSION_NOTEBOOK_V1",notebook_id="nb-1") is None
