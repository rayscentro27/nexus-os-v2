from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from nexus_agent_platform.durable_objective_control import (
    ObjectiveControlError, authorize_coding_action, authorize_job_start,
    complete_current_and_create_next, complete_intermediate_job, ensure_v5_record,
    finish_campaign, load_active_campaign, persist_campaign, recover_after_context_compaction, recover_worker_context,
)


def state_at(tmp_path):
    path = tmp_path / "v5.json"
    path.write_text(json.dumps({
        "CERTIFICATION_ID": "NEXUS-OWNER-REAL-WORLD-V5-20261010-6fb82fd9",
        "CURRENT_PHASE": "PHASE_3_GLOBAL_ONLINE_BUSINESS_RESEARCH",
        "LAST_COMPLETED_PHASE": "PHASE_1_SYSTEMS_CHECK_AND_RESEARCH_ROUTE_DIAGNOSIS",
        "JOB_IDS": ["job_e33989d3e27e4dc89b1c976aabd9d5da", "job_old_v2_visibility"],
        "STATUS": "IN_PROGRESS",
    }))
    return path


def ready(path):
    return ensure_v5_record(path)


def test_context_compaction_uses_v5_durable_identity_and_ignores_stale_v2(tmp_path):
    path = state_at(tmp_path); state = ready(path)
    compacted = recover_after_context_compaction({"campaign_id": "V2_CAMPAIGN",
        "objective_id": "v2_business_campaign_visibility", "objective_version": "V2",
        "task": "open the V2 campaign page"}, path)
    assert compacted["campaign_id"] == state["CAMPAIGN_ID"]
    assert compacted["master_objective"] == "NEXUS FULL OWNER-REQUEST REAL-WORLD CERTIFICATION V5"
    assert compacted["stale_context_ignored"] is True
    recovered = recover_worker_context(worker_id="codex", job_id=state["CURRENT_JOB_ID"],
        campaign_id=state["CAMPAIGN_ID"], objective_id=state["OWNER_OBJECTIVE_ID"],
        objective_version="V5", worker_role="CODING_AND_SYSTEM_REPAIR_ONLY", path=path)
    assert recovered["master_objective"] == "NEXUS FULL OWNER-REQUEST REAL-WORLD CERTIFICATION V5"
    assert recovered["ignore_stale_task"] is True
    assert "job_old_v2_visibility" not in state["COMPLETED_JOBS"]


def test_process_restart_reloads_same_campaign_job_and_checkpoint(tmp_path):
    path = state_at(tmp_path); before = ready(path)
    reinitialized = ensure_v5_record(path)
    root = __import__("pathlib").Path(__file__).resolve().parents[3]
    code = ("import json,sys; from pathlib import Path; "
            "from nexus_agent_platform.durable_objective_control import load_active_campaign; "
            "s=load_active_campaign(Path(sys.argv[1])); "
            "print(json.dumps({k:s[k] for k in ('CAMPAIGN_ID','OWNER_OBJECTIVE_ID','CURRENT_JOB_ID','CHECKPOINT')}))")
    env = {**os.environ, "PYTHONPATH": str(root / "scripts")}
    restarted = json.loads(subprocess.check_output([sys.executable, "-c", code, str(path)], env=env, text=True))
    assert reinitialized["CURRENT_JOB_ID"] == before["CURRENT_JOB_ID"]
    assert restarted["CAMPAIGN_ID"] == before["CAMPAIGN_ID"]
    assert restarted["OWNER_OBJECTIVE_ID"] == before["OWNER_OBJECTIVE_ID"]
    assert restarted["CURRENT_JOB_ID"] == before["CURRENT_JOB_ID"]
    assert restarted["CHECKPOINT"] == before["CHECKPOINT"]


def test_stale_v2_task_is_suppressed_by_campaign_objective_and_version_checks(tmp_path):
    path = state_at(tmp_path); state = ready(path)
    with pytest.raises(ObjectiveControlError, match="WORKER_CAMPAIGN_OR_OBJECTIVE_MISMATCH"):
        recover_worker_context(worker_id="codex", job_id="v2_job", campaign_id="V2_CAMPAIGN",
            objective_id="v2_business_campaign_visibility", objective_version="V2",
            worker_role="CODING_AND_SYSTEM_REPAIR_ONLY", path=path)
    assert state["MASTER_OBJECTIVE"] == "NEXUS FULL OWNER-REQUEST REAL-WORLD CERTIFICATION V5"


def test_intermediate_completion_creates_next_job_without_terminating_campaign(tmp_path):
    state = ready(state_at(tmp_path))
    next_job = {"job_id": "job_v5_next_research", "job_type": "RESEARCH_SOURCE_REVIEW",
                "department": "RESEARCH", "worker": "Nexus Research", "worker_role": "DEPARTMENT_EXECUTION"}
    advanced = complete_intermediate_job(state, job_id=state["CURRENT_JOB_ID"], next_job=next_job)
    assert advanced["CAMPAIGN_STATUS"] == "ACTIVE"
    assert advanced["TERMINAL_CONDITION_SATISFIED"] == "NO"
    assert advanced["CURRENT_JOB_ID"] == next_job["job_id"]
    assert advanced["NEXT_REQUIRED_JOB"] == next_job
    assert finish_campaign(advanced, all_required_jobs_complete=False,
                           complete_owner_experience=False)["CAMPAIGN_STATUS"] == "ACTIVE"


def test_campaign_terminal_guard_requires_all_jobs_and_owner_experience(tmp_path):
    state = ready(state_at(tmp_path))
    assert finish_campaign(state, all_required_jobs_complete=True,
                           complete_owner_experience=False)["CAMPAIGN_STATUS"] == "ACTIVE"
    terminal = finish_campaign(state, all_required_jobs_complete=True,
                               complete_owner_experience=True)
    assert terminal["TERMINAL_CONDITION_SATISFIED"] == "YES"
    assert terminal["CAMPAIGN_STATUS"] == "COMPLETE"


def test_false_local_final_status_cannot_persist_as_campaign_completion(tmp_path):
    path = state_at(tmp_path); state = ready(path)
    state["CAMPAIGN_STATUS"] = "COMPLETE"
    state["FINAL_STATUS"] = "BUSINESS_CAMPAIGN_VISIBLE_TO_RAY"
    state["TERMINAL_CONDITION_SATISFIED"] = "NO"
    with pytest.raises(ObjectiveControlError, match="FALSE_CAMPAIGN_TERMINATION_REJECTED"):
        persist_campaign(state, path)
    assert load_active_campaign(path)["CAMPAIGN_STATUS"] == "ACTIVE"


def test_controller_enqueues_next_job_with_same_campaign_identity(tmp_path):
    state = ready(state_at(tmp_path)); captured = {}
    class Created:
        job_id = "job_actual_next"
    def enqueue(**kwargs):
        captured.update(kwargs); return Created()
    next_job = {"job_type": "NEXUS_DEPARTMENT_QUERY", "department": "RESEARCH",
                "payload_ref": "reports/certification/v5/jobs/research_payload.json"}
    advanced = complete_current_and_create_next(state, job_id=state["CURRENT_JOB_ID"],
        next_job=next_job, enqueue=enqueue)
    assert captured["governance_context"]["campaign_id"] == state["CAMPAIGN_ID"]
    assert captured["governance_context"]["owner_objective_id"] == state["OWNER_OBJECTIVE_ID"]
    assert advanced["CURRENT_JOB_ID"] == "job_actual_next"
    assert advanced["TERMINAL_CONDITION_SATISFIED"] == "NO"


def test_durable_worker_must_match_active_campaign_job_and_version(tmp_path):
    from types import SimpleNamespace
    path = state_at(tmp_path); state = ready(path)
    context = {"campaign_id": state["CAMPAIGN_ID"], "owner_objective_id": state["OWNER_OBJECTIVE_ID"],
               "objective_version": "V5"}
    job = SimpleNamespace(job_id=state["CURRENT_JOB_ID"], governance_context=context)
    assert authorize_job_start(job, path=path)["ignore_stale_task"] is True
    job.governance_context = {**context, "campaign_id": "V2"}
    with pytest.raises(ObjectiveControlError, match="JOB_NOT_BOUND_TO_ACTIVE_CAMPAIGN"):
        authorize_job_start(job, path=path)


def test_live_nova_bounded_research_assignment_can_run_without_advancing_active_campaign(tmp_path):
    from types import SimpleNamespace
    path=state_at(tmp_path); state=ready(path)
    job=SimpleNamespace(job_id="nova-research-job",department="RESEARCH",
        job_type="RESEARCH_GAP_VERIFY",parent_job_id=None,
        governance_context={"source":"NOVA_MCP_RESEARCH_ASSIGNMENT","objective_id":"nova_research_test",
            "spend_allowed":False,"external_actions_allowed":False,"paid_provider_authorized":False})
    result=authorize_job_start(job,path=path)
    assert result["nova_research_assignment"] is True
    assert load_active_campaign(path)["CURRENT_JOB_ID"] == state["CURRENT_JOB_ID"]


def test_nova_research_assignment_guard_rejects_spend_or_other_job_types(tmp_path):
    from types import SimpleNamespace
    path=state_at(tmp_path); ready(path)
    context={"source":"NOVA_MCP_RESEARCH_ASSIGNMENT","objective_id":"nova_research_test",
        "spend_allowed":False,"external_actions_allowed":False,"paid_provider_authorized":False}
    job=SimpleNamespace(job_id="nova-research-job",department="RESEARCH",
        job_type="RESEARCH_GAP_VERIFY",parent_job_id=None,governance_context={**context,"spend_allowed":True})
    with pytest.raises(ObjectiveControlError,match="JOB_NOT_BOUND_TO_ACTIVE_CAMPAIGN"):
        authorize_job_start(job,path=path)
    job.governance_context=context; job.job_type="TRADING_BACKTEST"
    with pytest.raises(ObjectiveControlError,match="JOB_NOT_BOUND_TO_ACTIVE_CAMPAIGN"):
        authorize_job_start(job,path=path)


def test_legacy_nova_assignment_provenance_is_bounded_and_allowed(tmp_path):
    from types import SimpleNamespace
    path=state_at(tmp_path); ready(path)
    job=SimpleNamespace(job_id="legacy-nova-job",department="RESEARCH",
        job_type="RESEARCH_GAP_VERIFY",parent_job_id=None,
        governance_context={"source":"NOVA_MCP_RESEARCH_ASSIGNMENT","objective_id":"nova_research_test",
            "external_actions_authorized":False,"paid_provider_authorized":False})
    assert authorize_job_start(job,path=path)["nova_research_assignment"] is True


def test_research_completion_notice_is_narrowly_allowed_as_independent_campaign_work(tmp_path):
    from types import SimpleNamespace
    path=state_at(tmp_path); state=ready(path)
    job=SimpleNamespace(job_id="nova-research-notice",job_type="NOVA_RESEARCH_RESULT_NOTICE",
        parent_job_id=state["CURRENT_JOB_ID"],governance_context={
            "campaign_id":state["CAMPAIGN_ID"],"owner_objective_id":state["OWNER_OBJECTIVE_ID"],
            "objective_version":state.get("OBJECTIVE_VERSION"),"independent_job":True,"spend_allowed":False,
            "paid_provider_authorized":False,"external_actions_allowed":True,"source":"NEXUS_RESEARCH_COMPLETION_NOTICE",
            "completed_research_job_id":"job_research_done",
            "completed_research_receipt_id":"receipt_research_done"})
    assert authorize_job_start(job,path=path)["independent_parallel_job"] is True
    job.governance_context={**job.governance_context,"completed_research_receipt_id":""}
    with pytest.raises(ObjectiveControlError,match="JOB_NOT_BOUND_TO_ACTIVE_CAMPAIGN"):
        authorize_job_start(job,path=path)


def test_resource_independent_parallel_job_is_allowed_but_paused_dependency_is_not(tmp_path):
    from types import SimpleNamespace
    path=state_at(tmp_path); state=ready(path)
    state["WAITING_RESOURCE_JOBS"]=[{"job_id":state["CURRENT_JOB_ID"],
        "resource":"NOTEBOOKLM","status":"WAITING_RESOURCE_WINDOW"}]
    persist_campaign(state,path)
    context={"campaign_id":state["CAMPAIGN_ID"],"owner_objective_id":state["OWNER_OBJECTIVE_ID"],
        "objective_version":"V5","independent_job":True,"spend_allowed":False,
        "external_actions_allowed":False,"resource_dependencies":["SEARXNG"]}
    parallel=SimpleNamespace(job_id="job_public_research",parent_job_id=state["CURRENT_JOB_ID"],governance_context=context)
    result=authorize_job_start(parallel,path=path)
    assert result["independent_parallel_job"] is True
    parallel.governance_context={**context,"resource_dependencies":["NOTEBOOKLM"]}
    with pytest.raises(ObjectiveControlError,match="JOB_NOT_BOUND_TO_ACTIVE_CAMPAIGN"):
        authorize_job_start(parallel,path=path)


def test_only_completed_bounded_notebook_canary_may_run_nested_needle_child(tmp_path):
    from types import SimpleNamespace
    path=state_at(tmp_path); state=ready(path)
    parent=SimpleNamespace(job_id="job_canary",state="COMPLETED",department="RESEARCH",
        job_type="NEXUS_NOTEBOOKLM_RUNTIME_CANARY",parent_job_id=state["CURRENT_JOB_ID"],
        governance_context={"campaign_id":state["CAMPAIGN_ID"],
            "owner_objective_id":state["OWNER_OBJECTIVE_ID"],
            "objective_version":state["OBJECTIVE_VERSION"],
            "source":"NOVA_MCP_NOTEBOOKLM_CANARY","runtime_restoration_canary":True,
            "spend_allowed":False,"paid_provider_authorized":False,
            "external_actions_allowed":False,"resource_dependencies":["NOTEBOOKLM"]})
    child=SimpleNamespace(job_id="job_needle",state="CLAIMED",department="RESEARCH",
        job_type="NEEDLE_RESEARCH_READINESS_VERIFY",parent_job_id=parent.job_id,
        governance_context={"campaign_id":state["CAMPAIGN_ID"],
            "owner_objective_id":state["OWNER_OBJECTIVE_ID"],
            "objective_version":state["OBJECTIVE_VERSION"],
            "source":"NOTEBOOK_COMPLETION_CONTRACT_NEEDLE",
            "runtime_restoration_canary":True,"independent_job":True,
            "no_new_owner_objective":True,"spend_allowed":False,
            "paid_provider_authorized":False,"external_actions_allowed":False,
            "research_case_id":"isolated-case","contract_completion_receipt_id":"ncc-receipt",
                "repair_attempt":0,
            "resource_dependencies":["OPENAI_CODEX"]})
    class Store:
        def get(self, job_id):
            return parent if job_id==parent.job_id else None
    authorized=authorize_job_start(child,path=path,store=Store())
    assert authorized["bounded_runtime_canary_child"] is True
    assert authorized["independent_parallel_job"] is True
    child.governance_context={**child.governance_context,"spend_allowed":True}
    with pytest.raises(ObjectiveControlError,match="JOB_NOT_BOUND_TO_ACTIVE_CAMPAIGN"):
        authorize_job_start(child,path=path,store=Store())


def test_one_targeted_needle_repair_and_recheck_keep_same_bounded_lineage(tmp_path):
    from types import SimpleNamespace
    path=state_at(tmp_path); state=ready(path)
    root_context={"campaign_id":state["CAMPAIGN_ID"],"owner_objective_id":state["OWNER_OBJECTIVE_ID"],
        "objective_version":state["OBJECTIVE_VERSION"],"source":"NOVA_MCP_NOTEBOOKLM_CANARY",
        "runtime_restoration_canary":True,"spend_allowed":False,"paid_provider_authorized":False,
        "external_actions_allowed":False,"resource_dependencies":["NOTEBOOKLM"]}
    root=SimpleNamespace(job_id="canary",state="COMPLETED",department="RESEARCH",
        job_type="NEXUS_NOTEBOOKLM_RUNTIME_CANARY",parent_job_id=state["CURRENT_JOB_ID"],
        governance_context=root_context)
    common={"campaign_id":state["CAMPAIGN_ID"],"owner_objective_id":state["OWNER_OBJECTIVE_ID"],
        "objective_version":state["OBJECTIVE_VERSION"],"source":"NOTEBOOK_COMPLETION_CONTRACT_NEEDLE",
        "runtime_restoration_canary":True,"independent_job":True,"no_new_owner_objective":True,
        "spend_allowed":False,"paid_provider_authorized":False,"external_actions_allowed":False,
        "research_case_id":"case","contract_completion_receipt_id":"contract-receipt"}
    initial=SimpleNamespace(job_id="needle-0",state="COMPLETED",department="RESEARCH",
        job_type="NEEDLE_RESEARCH_READINESS_VERIFY",parent_job_id=root.job_id,
        governance_context={**common,"repair_attempt":0,"resource_dependencies":["OPENAI_CODEX"]})
    repair=SimpleNamespace(job_id="repair-1",state="COMPLETED",department="RESEARCH",
        job_type="NEEDLE_RESEARCH_TARGETED_REPAIR",parent_job_id=initial.job_id,
        governance_context={**common,"repair_attempt":1,"resource_dependencies":["NOTEBOOKLM"]})
    recheck=SimpleNamespace(job_id="needle-1",state="READY",department="RESEARCH",
        job_type="NEEDLE_RESEARCH_READINESS_VERIFY",parent_job_id=repair.job_id,
        governance_context={**common,"repair_attempt":1,"resource_dependencies":["OPENAI_CODEX"]})
    class Store:
        jobs={root.job_id:root,initial.job_id:initial,repair.job_id:repair}
        def get(self, job_id): return self.jobs.get(job_id)
    assert authorize_job_start(recheck,path=path,store=Store())["bounded_runtime_canary_child"] is True
    repair.governance_context={**repair.governance_context,"spend_allowed":True}
    with pytest.raises(ObjectiveControlError,match="JOB_NOT_BOUND_TO_ACTIVE_CAMPAIGN"):
        authorize_job_start(recheck,path=path,store=Store())


def test_coding_role_guard_allows_repair_blocks_department_substitution(tmp_path):
    path = state_at(tmp_path); state = ready(path)
    common = dict(campaign_id=state["CAMPAIGN_ID"], objective_id=state["OWNER_OBJECTIVE_ID"],
        job_id=state["CURRENT_JOB_ID"], objective_version="V5",
        worker_role="CODING_AND_SYSTEM_REPAIR_ONLY", path=path)
    assert authorize_coding_action(**common, action_summary="repair durable campaign controller")
    with pytest.raises(ObjectiveControlError, match="CODEX_DEPARTMENT_SUBSTITUTION_BLOCKED"):
        authorize_coding_action(**common, action_summary="create marketing campaign and creative asset")


def test_codex_opencode_failover_reuses_same_durable_job_and_checkpoint(tmp_path):
    from nexus_agent_platform.coding_worker_supervisor import CodingTask, persist_handoff
    path = state_at(tmp_path); state = ready(path)
    codex = recover_worker_context(worker_id="codex", job_id=state["CURRENT_JOB_ID"],
        campaign_id=state["CAMPAIGN_ID"], objective_id=state["OWNER_OBJECTIVE_ID"],
        objective_version="V5", worker_role="CODING_AND_SYSTEM_REPAIR_ONLY", path=path)
    opencode = recover_worker_context(worker_id="opencode", job_id=state["CURRENT_JOB_ID"],
        campaign_id=state["CAMPAIGN_ID"], objective_id=state["OWNER_OBJECTIVE_ID"],
        objective_version="V5", worker_role="CODING_AND_SYSTEM_REPAIR_ONLY", path=path)
    assert codex["job_id"] == opencode["job_id"]
    assert codex["checkpoint"] == opencode["checkpoint"]
    assert codex["objective_id"] == opencode["objective_id"]
    task = CodingTask(task_id="repair-assignment", objective_id=state["OWNER_OBJECTIVE_ID"],
        prompt="repair controller", allowed_paths=("scripts/nexus_agent_platform/",),
        protected_paths=("secrets/",), acceptance=("focused tests pass",), checkpoint_sha="a"*40,
        campaign_id=state["CAMPAIGN_ID"], owner_objective_id=state["OWNER_OBJECTIVE_ID"],
        objective_version="V5", job_id=state["CURRENT_JOB_ID"])
    handoff = persist_handoff(task=task, previous_worker="codex", next_worker="opencode",
        reason="RATE_LIMITED", failure_class="RATE_LIMITED", failure_evidence="simulated 429",
        current_stage="S2_HANDOFF_CREATED", completed_stages=["S0_SCHEDULED", "S1_REPAIR_STARTED"])
    assert handoff["campaign_id"] == state["CAMPAIGN_ID"]
    assert handoff["owner_objective_id"] == state["OWNER_OBJECTIVE_ID"]
    assert handoff["job_id"] == state["CURRENT_JOB_ID"]
    assert handoff["checkpoint_sha"] == task.checkpoint_sha
    assert handoff["next_worker"] == "opencode"
