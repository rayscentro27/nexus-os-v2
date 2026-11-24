import types

from nexus_agent_platform import durable_jobs, workflow_execution
from nexus_agent_platform import needle_research_workflow as needle_jobs


def test_needle_job_types_use_existing_research_worker_and_execution_classes():
    assert durable_jobs.handler_route("NEEDLE_RESEARCH_READINESS_VERIFY") == "NEEDLE_RESEARCH"
    assert durable_jobs.handler_route("NEEDLE_RESEARCH_TARGETED_REPAIR") == "NEEDLE_RESEARCH"
    assert workflow_execution._JOB_CLASSES["NEEDLE_RESEARCH_READINESS_VERIFY"] == "LIGHT_REASONING"
    assert workflow_execution._JOB_CLASSES["NEEDLE_RESEARCH_TARGETED_REPAIR"] == "SPECIALIZED_EXECUTOR"


def test_local_group_turn_statuses_are_deterministically_reconciled(tmp_path,monkeypatch):
    import json
    monkeypatch.setattr(needle_jobs,"ROOT",tmp_path)
    from research import notebook_completion_contracts as contracts
    state=contracts.new_contract_state(objective="Research one opportunity",research_purpose="MISSION_RESEARCH",
        research_domain="BUSINESS_OPPORTUNITY",notebook_id="nb-same")
    first=state["required_questions"][0]
    ref="data/runtime/notebook_answer_artifacts/case/turn.json"
    path=tmp_path/ref; path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"answer":"```json\n"+json.dumps({"question_results":[{
        "question_id":first["question_id"],"evidence_status":"PARTIALLY_VERIFIED"}]})+"\n```"}))
    case={"notebook_answers":[{"question_type":"CONTRACT_GROUP:BUSINESS_OPPORTUNITY_MISSION_NOTEBOOK_V1:GROUP_A_DEFINITION",
        "local_artifact_ref":ref,"source_ids":["source-a"]}]}
    changed=needle_jobs._reconcile_local_group_statuses("case",state,case)
    assert changed==1
    assert first["evidence_status"]=="PARTIALLY_VERIFIED"
    assert first["source_refs"]==["source-a"]


def test_enqueue_creates_idempotent_child_on_existing_queue_without_objective(monkeypatch):
    calls = {}
    parent = types.SimpleNamespace(job_id="research-job", correlation_id="mission-1",
        governance_context={"owner_objective_id": "owner-1", "source": "RESEARCH",
            "notebooklm_policy_job_type":"NEXUS_FULL_RESEARCH_CANARY_TEST"})
    created = types.SimpleNamespace(job_id="needle-job", job_type="NEEDLE_RESEARCH_READINESS_VERIFY",
        state="READY", payload_ref="needle.json", parent_job_id="research-job",
        correlation_id="mission-1", governance_context={})

    class Store:
        def set_governance_context(self, job_id, context):
            calls["governance"] = context
        def get(self, job_id):
            return created

    store = Store()
    def write_payload(payload):
        calls["payload"] = payload
        return "needle.json"
    monkeypatch.setattr(needle_jobs, "_write_payload", write_payload)
    monkeypatch.setattr(durable_jobs, "default_store", lambda: store)
    def create_next_job(actual_store, actual_parent, **kwargs):
        calls["create"] = (actual_store, actual_parent, kwargs)
        return created
    monkeypatch.setattr(durable_jobs, "create_next_job", create_next_job)

    result = needle_jobs.enqueue_job(case_id="case-1", job_type="NEEDLE_RESEARCH_READINESS_VERIFY",
        completion_receipt_id="ncc-1", parent_job=parent)

    assert result["job_id"] == "needle-job"
    assert calls["create"][0] is store and calls["create"][1] is parent
    assert calls["create"][2]["department"] == "RESEARCH"
    assert calls["create"][2]["event_id"] == "case-1:ncc-1:NEEDLE_RESEARCH_READINESS_VERIFY:repair-0"
    assert calls["payload"]["no_new_owner_objective"] is True
    assert calls["payload"]["notebooklm_policy_job_type"] == "NEXUS_FULL_RESEARCH_CANARY_TEST"
    assert calls["governance"]["no_new_owner_objective"] is True
    assert calls["governance"]["notebooklm_policy_job_type"] == "NEXUS_FULL_RESEARCH_CANARY_TEST"


def test_incomplete_mechanical_contract_blocks_before_semantic_verifier(monkeypatch, tmp_path):
    from research import notebook_completion_contracts as contracts
    state = {"research_job_id": "research-job", "contract_id": "BUSINESS_OPPORTUNITY_MISSION_NOTEBOOK_V1",
        "notebook_id": "nb-existing", "required_questions": [{"question_id": "Q1", "required": True, "asked": False}]}
    monkeypatch.setattr(needle_jobs, "_load_payload", lambda job: {"case_id": "case-1", "completion_receipt_id": "ncc-1"})
    monkeypatch.setattr(contracts, "load_state", lambda case_id: state)
    monkeypatch.setattr(contracts, "verify_completion", lambda *a, **k: {"complete": False, "missing": ["Q1"]})
    monkeypatch.setattr(contracts, "persist_state", lambda *a, **k: "local-state.json")
    monkeypatch.setattr(needle_jobs, "_save_case", lambda *a, **k: None)
    def should_not_run(*args, **kwargs):
        raise AssertionError("semantic model verifier called before mechanical gate")
    monkeypatch.setattr("research.needle_research_readiness.verify_readiness", should_not_run)

    result = needle_jobs.handle_job(types.SimpleNamespace(job_type="NEEDLE_RESEARCH_READINESS_VERIFY",
        payload_ref="payload.json"), object())
    assert result["reason"] == "MECHANICAL_NOTEBOOK_CONTRACT_GATE_FAILED"
    assert result["mechanical_verification"]["complete"] is False


def _complete_forex_state():
    from research.notebook_completion_contracts import new_contract_state, compact_handoff
    state = new_contract_state(objective="Research a Forex strategy for deterministic testing",
        research_purpose="MISSION_RESEARCH", research_domain="FOREX", notebook_id="nb-same",
        research_job_id="research-job")
    for row in state["required_questions"]:
        row.update(asked=True, answer_status="UNVERIFIED", evidence_status="UNVERIFIED",
            supplementation_attempted=True, source_refs=["public-source-1"])
    state["evidence_gaps"] = [{"question_id": "FOREX_Q01", "reviewed": True,
        "supplementation_attempted": True, "evidence_status": "UNVERIFIED",
        "unresolved_note": "Instrument assumptions remain unverified."}]
    state["synthesis"] = "Rules and limitations for the proposed strategy."
    state["action_statement"] = {key: "explicit and bounded" for key in
        __import__("research.notebook_completion_contracts", fromlist=["CONTRACTS"]).CONTRACTS[state["contract_id"]]["action_fields"]}
    state["structured_extraction"] = {"instrument": "EURUSD", "unresolved": ["spread source"]}
    state["handoff_package"] = compact_handoff(state, receipt_id="ncc-receipt")
    return state


def test_ready_routes_compact_handoff_to_contract_department_without_alpha(monkeypatch):
    from research import notebook_completion_contracts as contracts
    state = _complete_forex_state()
    monkeypatch.setattr(needle_jobs, "_load_payload", lambda job: {"case_id": "case-forex",
        "completion_receipt_id": "ncc-receipt", "repair_attempt": 0})
    monkeypatch.setattr(contracts, "load_state", lambda case_id: state)
    monkeypatch.setattr(contracts, "verify_completion", lambda *a, **k: {"complete": True})
    monkeypatch.setattr(contracts, "persist_state", lambda *a, **k: "local-checkpoint.json")
    monkeypatch.setattr(contracts, "finalize_contract", lambda *a, **k: {"ok": True})
    monkeypatch.setattr(needle_jobs, "_save_case", lambda *a, **k: None)
    monkeypatch.setattr("research.needle_research_readiness.verify_readiness", lambda *a, **k: {
        "status": "READY_FOR_DEPARTMENT", "receipt_id": "needle-receipt", "reason_code": "READY",
        "summary": "Trading can implement with explicit limitations.", "next_department": "TRADING",
        "notebook_id": "nb-same", "execution_class": "LIGHT_REASONING", "provider": "openai-codex",
        "model": "gpt-5.5", "cost_class": "EXISTING_BUDGET", "latency_ms": 1})
    captured = {}
    from operations import nexus_handoff
    monkeypatch.setattr(nexus_handoff, "configured", lambda: True)
    def create_handoff(**kwargs):
        captured.update(kwargs)
        return {"handoff_id": "handoff-1", "status": "PERSISTED"}
    monkeypatch.setattr(nexus_handoff, "create_handoff", create_handoff)

    result = needle_jobs.handle_job(types.SimpleNamespace(job_type="NEEDLE_RESEARCH_READINESS_VERIFY",
        payload_ref="needle-job.json"), object())

    assert result["needle_status"] == "READY_FOR_DEPARTMENT"
    assert result["next_department"] == "TRADING"
    assert captured["target_department"] == "TRADING"
    assert captured["handoff_type"] == "NOTEBOOK_COMPLETION_CONTRACT"
    assert "notebook_contract" in captured["payload"]
    assert "Alpha" not in captured["target_department"]


def test_research_more_queues_one_targeted_repair_for_same_case_and_notebook(monkeypatch):
    from research import notebook_completion_contracts as contracts
    state = _complete_forex_state()
    state["evidence_gaps"] = [{"question_id": state["required_questions"][0]["question_id"],
        "reviewed": True, "supplementation_attempted": True, "evidence_status": "UNVERIFIED",
        "unresolved_note": "Need official spread evidence."}]
    monkeypatch.setattr(needle_jobs, "_load_payload", lambda job: {"case_id": "case-forex",
        "completion_receipt_id": "ncc-receipt", "repair_attempt": 0})
    monkeypatch.setattr(contracts, "load_state", lambda case_id: state)
    monkeypatch.setattr(contracts, "verify_completion", lambda *a, **k: {"complete": True})
    monkeypatch.setattr(contracts, "persist_state", lambda *a, **k: "local-checkpoint.json")
    monkeypatch.setattr(needle_jobs, "_save_case", lambda *a, **k: None)
    question_id = state["required_questions"][0]["question_id"]
    monkeypatch.setattr("research.needle_research_readiness.verify_readiness", lambda *a, **k: {
        "status": "RESEARCH_MORE", "receipt_id": "needle-receipt", "reason_code": "SPREAD_EVIDENCE_GAP",
        "summary": "One material implementation assumption needs a targeted lookup.",
        "affected_question_ids": [question_id], "specific_gap": "The spread assumption lacks an official or provider source.",
        "requested_research_action": "Find the official instrument specification for the selected provider and record the observed spread basis.",
        "evidence_needed": "Official provider instrument documentation.", "next_department": "TRADING",
        "notebook_id": "nb-same", "execution_class": "LIGHT_REASONING"})
    queued = {}
    def enqueue(**kwargs):
        queued.update(kwargs)
        return {"job_id": "repair-job", "job_type": kwargs["job_type"], "state": "READY"}
    monkeypatch.setattr(needle_jobs, "enqueue_job", enqueue)

    result = needle_jobs.handle_job(types.SimpleNamespace(job_type="NEEDLE_RESEARCH_READINESS_VERIFY",
        payload_ref="needle-job.json", governance_context={}), object())

    assert result["needle_status"] == "RESEARCH_MORE"
    assert queued["case_id"] == "case-forex"
    assert queued["job_type"] == "NEEDLE_RESEARCH_TARGETED_REPAIR"
    assert queued["repair_attempt"] == 1
    assert queued["needle_request"]["notebook_id"] == "nb-same"
    assert queued["needle_request"]["affected_question_ids"] == [question_id]
    assert queued["needle_request"]["requested_research_action"].startswith("Find the official")
    assert result["next_job_id"] == "repair-job"

