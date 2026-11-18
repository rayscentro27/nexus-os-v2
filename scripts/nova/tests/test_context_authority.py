import json
import os

from nova.context_authority import resolve_context, render_context_block
from types import SimpleNamespace

from nova import nova_telegram_worker as worker
from nova import operator_v1 as op


def test_immediate_assistant_answer_outranks_historical_memory():
    previous = {"update_id": 7, "user_text": "What are you working on?",
                "assistant_text": "The objective reached a verified technical boundary."}
    result = resolve_context("Can you summarize that in one sentence?", previous_turn=previous,
                             long_term_memory="Ray was feeling great over coffee earlier.")
    assert result["reference_type"] == "IMMEDIATE_REFERENT"
    assert result["context_source"] == "PREVIOUS_ASSISTANT_TURN"
    assert "verified technical boundary" in result["resolved_referent"]["assistant_text"]


def test_right_now_uses_live_state_and_not_old_blocked_memory():
    result = resolve_context("What are you working on right now?",
                             active_mission={"status": "NO_ACTIVE_MISSION"},
                             recent_completed_mission={"mission_id": "done-1", "status": "COMPLETE"},
                             long_term_memory={"status": "RECOVERING", "mission_id": "old-blocked"})
    assert result["reference_type"] == "CURRENT_STATE"
    assert result["resolved_referent"]["status"] == "NO_ACTIVE_MISSION"


def test_next_step_without_active_objective_is_a_suggestion():
    result = resolve_context("What would be a useful next step?", thread_context=None,
                             long_term_memory={"goal": "old $500 website inquiry"})
    assert result["context_source"] == "OPTIONAL_SUGGESTION"
    assert result["resolved_referent"] is None


def test_immediate_thread_can_ground_next_step_without_claiming_active_work():
    result = resolve_context("What would be a useful next step?", thread_context={
        "previous_user_text": "What does Nexus do?", "previous_assistant_text": "Nexus coordinates work."})
    assert result["context_source"] == "CURRENT_THREAD_CONTEXT"


def test_entity_followup_resolves_exact_lineage_before_memory():
    result = resolve_context("Continue that case", previous_turn={"assistant_text": "The case is case-old."},
                             entity_lineage={"case_id": "case-exact"},
                             long_term_memory={"case_id": "case-similar"})
    assert result["resolved_entity_type"] == "RESEARCH_CASE"
    assert result["resolved_entity_id"] == "case-exact"


def test_recent_completed_work_uses_latest_verified_mission():
    result = resolve_context("What was the last mission you completed?",
        active_mission={"mission_id": "active-1"},
        recent_completed_mission={"mission_id": "done-1", "status": "COMPLETE", "mission_success_verified": True})
    assert result["reference_type"] == "RECENT_COMPLETED_WORK"
    assert result["resolved_referent"]["mission_id"] == "done-1"


def test_why_complete_uses_immediate_referent_and_authoritative_verified_snapshot():
    previous = {"assistant_text": "The last mission was reported as a technical limit. Mission ID: done-1"}
    result = resolve_context("Why was that considered complete?", previous_turn=previous,
        recent_completed_mission={"mission_id":"done-1","status":"COMPLETE","success_verified":True,
            "success_condition":"case reaches recommendation ready","final_outcome":"PARK recommendation persisted"})
    assert result["reference_type"] == "COMPLETION_EXPLANATION"
    assert result["context_source"] == "PREVIOUS_ASSISTANT_TURN+AUTHORITATIVE_MISSION_SNAPSHOT"
    assert result["resolved_referent"]["mission_snapshot"]["final_outcome"] == "PARK recommendation persisted"


def test_historical_problem_query_keeps_events_distinct_from_terminal_state():
    result = resolve_context("Did that mission hit any technical problems before it completed?",
        previous_turn={"assistant_text":"The last mission completed."},
        recent_completed_mission={"mission_id":"done-1","status":"COMPLETE","success_verified":True,
            "historical_problem_events":[{"event_type":"MISSION_RECOVERING"}]})
    assert result["reference_type"] == "HISTORICAL_MISSION_EVENTS"
    assert result["resolved_referent"]["mission_snapshot"]["status"] == "COMPLETE"


def test_followup_why_resolves_to_previous_result_and_shortening_to_previous_answer():
    previous = {"user_text": "Tell me about the last Research result.",
                "assistant_text": "The result ended because the source evidence was incomplete."}
    why = resolve_context("Why did it end that way?", previous_turn=previous,
                          long_term_memory="The coffee earlier was enjoyable.")
    shorter = resolve_context("Make that shorter.", previous_turn={"assistant_text": "Nexus coordinates teams and tools."})
    assert why["context_source"] == "PREVIOUS_ASSISTANT_TURN"
    assert "source evidence" in why["resolved_referent"]["assistant_text"]
    assert "Nexus coordinates" in shorter["resolved_referent"]["assistant_text"]


def test_context_block_marks_snapshot_authoritative_over_hermes_history():
    block = render_context_block({"message_id": "9", "previous_assistant_text": "Exact recent answer",
                                  "resolution_source": "PREVIOUS_ASSISTANT_TURN", "resolution_priority": 2})
    assert "do not let older session or personal memory override it" in block
    assert "Exact recent answer" in block


def test_previous_delivered_assistant_turn_is_loaded_for_same_chat(tmp_path, monkeypatch):
    deliveries = tmp_path / "delivery"
    missions = tmp_path / "missions"
    deliveries.mkdir()
    missions.mkdir()
    monkeypatch.setattr(worker, "NOVA_DELIVERY_DIR", str(deliveries))
    monkeypatch.setattr(worker, "NOVA_MISSIONS_DIR", str(missions))
    (deliveries / "40.json").write_text('{"chat_id":7,"state":"DELIVERED","mission_id":"m40","response":"The objective reached a verified technical boundary."}')
    (missions / "m40.json").write_text('{"original_message":"What are you working on right now?"}')
    (deliveries / "41.json").write_text('{"chat_id":8,"state":"DELIVERED","response":"Wrong chat"}')
    turn = worker._previous_delivered_turn(7, 42)
    assert turn["update_id"] == 40
    assert turn["user_text"] == "What are you working on right now?"
    assert turn["assistant_text"] == "The objective reached a verified technical boundary."


def test_hermes_call_receives_context_snapshot_and_keeps_mcp_lineage(monkeypatch):
    seen = {}
    result = SimpleNamespace(response="ok", status="SUCCEEDED", runtime_host="ORACLE",
        hermes_version="0.20.6", profile="nova_nexus", provider="openai-codex", model="gpt-5.6-terra",
        hermes_session_id="session", error=None, latency_ms=1)
    def run(message, session, **kwargs):
        seen.update(kwargs)
        return result
    monkeypatch.setattr("nexus_agent_platform.bridge.oracle_hermes_cli.run_oracle_hermes", run)
    snapshot = {"message_id":"50", "current_text":"Can you summarize that?",
        "previous_assistant_text":"The objective reached a verified technical boundary.",
        "resolution_source":"PREVIOUS_ASSISTANT_TURN", "resolution_priority":2,
        "reference_type":"IMMEDIATE_REFERENT"}
    worker._run_oracle_primary(50, {"message_id":50}, 7, "Can you summarize that?",
        mcp_action_route={"server_id":"canary"}, context_snapshot=snapshot)
    block = seen["pre_context"]
    assert "The objective reached a verified technical boundary." in block
    assert "CURRENT APPROVED MCP OBJECT LINEAGE" not in block or "server_id" in block


def test_current_operator_status_drops_older_same_lineage_recovery(tmp_path, monkeypatch):
    monkeypatch.setenv("NOVA_OPERATOR_DB", str(tmp_path / "operator.sqlite3"))
    db = op._connect()
    db.execute("""INSERT INTO operator_missions(mission_id,owner_id,objective_text,objective_type,status,
        understanding_json,created_at,updated_at,completed_at,mission_success_verified)
        VALUES(?,?,?,?,?,?,?,?,?,?)""", ("stale-recovery", "ray", "Inspect job_f7bd2919a42a484f93108ae1c39a507b",
        "ACTION", "RECOVERING", "{}", "2026-10-19T13:45:00Z", "2026-10-19T13:46:00Z", None, 0))
    db.execute("""INSERT INTO operator_missions(mission_id,owner_id,objective_text,objective_type,status,
        understanding_json,created_at,updated_at,completed_at,mission_success_verified)
        VALUES(?,?,?,?,?,?,?,?,?,?)""", ("verified-complete", "ray", "Research objective", "ACTION",
        "COMPLETE", "{}", "2026-10-19T14:00:00Z", "2026-10-19T14:01:00Z", "2026-10-19T14:01:00Z", 1))
    db.execute("INSERT INTO operator_lineage VALUES(?,?,?,?,?,?,?)", (
        "verified-complete", "RESEARCH_JOB", "job_f7bd2919a42a484f93108ae1c39a507b",
        "CURRENT_OBJECT", None, "2026-10-19T14:01:00Z", "{}"))
    db.commit()
    db.close()
    status = op.status_read(None, owner_id="ray")
    assert status["status"] == "NO_ACTIVE_MISSION"
    assert status["mission_id"] is None


def test_authoritative_snapshot_terminal_row_beats_older_boundary_event(tmp_path, monkeypatch):
    monkeypatch.setenv("NOVA_OPERATOR_DB", str(tmp_path / "operator.sqlite3"))
    db = op._connect()
    evidence = {"case_status":"RECOMMENDATION_READY","open_question_count":0,"source_count":4,
        "synthesis_count":2,"recommendation":"PARK","historical_exception_recoverable":False,
        "verified_case_id":"rcase-final","verified_at":"2026-10-19T21:08:22Z",
        "result":{"result_data":{"case_state":{"status":"RECOMMENDATION_READY","source_count":4,"synthesis_count":2,"open_questions":[]}}}}
    final = {"response":"PARK result verified; no open questions."}
    db.execute("""INSERT INTO operator_missions(mission_id,owner_id,objective_text,objective_type,status,
        understanding_json,created_at,updated_at,completed_at,mission_success_condition_json,
        mission_success_evidence_json,mission_success_verified,mission_completion_reason,final_result_json)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", ("done-1","ray","Complete same case","ACTION","COMPLETE",
        "{}","2026-10-19T20:00:00Z","2026-10-19T21:08:22Z","2026-10-19T21:08:22Z",
        json.dumps({"description":"same case recommendation ready and no questions"}),json.dumps(evidence),1,
        "EXACT_CASE_RESULT_VERIFIED",json.dumps(final)))
    db.execute("INSERT INTO operator_events VALUES(?,?,?,?,?,?)",(
        "event-old","done-1",None,"MISSION_BLOCKED_TRUE",json.dumps({"reason":"old boundary"}),"2026-10-19T20:10:00Z"))
    db.execute("INSERT INTO operator_events VALUES(?,?,?,?,?,?)",(
        "event-final","done-1",None,"MISSION_COMPLETE",json.dumps({"reason":"verified"}),"2026-10-19T21:08:22Z"))
    db.commit(); db.close()
    snapshot = op.get_authoritative_mission_snapshot("done-1", owner_id="ray")
    assert snapshot["status"] == "COMPLETE"
    assert snapshot["success_verified"] is True
    assert snapshot["terminal_reason"] == "EXACT_CASE_RESULT_VERIFIED"
    assert snapshot["final_entity_state"] == {"entity_type":"RESEARCH_CASE","entity_id":"rcase-final",
        "status":"RECOMMENDATION_READY","open_question_count":0,"source_count":4,
        "synthesis_count":2,"recommendation":"PARK","updated_at":None}
    assert [x["event_type"] for x in snapshot["historical_problem_events"]] == ["MISSION_BLOCKED_TRUE"]
    completed = op.recent_completed_status("ray")
    assert completed["final_outcome"] == "PARK result verified; no open questions."


def test_authoritative_state_answers_do_not_call_hermes_for_stale_status(tmp_path, monkeypatch):
    monkeypatch.setenv("NOVA_OPERATOR_DB", str(tmp_path / "operator.sqlite3"))
    db = op._connect(); db.close()
    monkeypatch.setattr(worker, "NOVA_DELIVERY_DIR", str(tmp_path / "delivery"))
    monkeypatch.setattr(worker, "NOVA_CONTEXT_DIR", str(tmp_path / "context"))
    monkeypatch.setattr(worker, "NOVA_MISSIONS_DIR", str(tmp_path / "missions"))
    snapshot = {"reference_type":"CURRENT_STATE","active_mission":{"status":"NO_ACTIVE_MISSION"}}
    assert worker._authoritative_mission_answer(snapshot) == "I don't currently have an active mission."
    completed = {"mission_id":"done-1","objective":"Continue the case","success_verified":True,
        "final_outcome":"PARK persisted","success_condition":"case recommendation ready",
        "final_entity_state":{"entity_type":"RESEARCH_CASE","entity_id":"case-1","status":"RECOMMENDATION_READY",
            "source_count":4,"synthesis_count":2,"open_question_count":0,"recommendation":"PARK"}}
    answer = worker._authoritative_mission_answer({"reference_type":"RECENT_COMPLETED_WORK","last_completed_mission":completed})
    assert "RECOMMENDATION_READY" in answer and "PARK recommendation" in answer
    why = worker._authoritative_mission_answer({"reference_type":"COMPLETION_EXPLANATION","authoritative_mission_snapshot":completed})
    assert "success condition was independently verified" in why
    assert "technical limit" not in why


def test_current_state_handler_uses_owner_delivery_context_without_creating_mission(monkeypatch):
    seen = {}
    monkeypatch.setattr(worker, "_acquire_chat_lock", lambda chat_id: True)
    monkeypatch.setattr(worker, "_release_chat_lock", lambda chat_id: None)
    monkeypatch.setattr(worker, "is_authorized", lambda *args: True)
    monkeypatch.setattr(worker, "load_current_objective_lineage", lambda chat_id: None)
    monkeypatch.setattr(op, "current_entity_lineage", lambda owner: None)
    monkeypatch.setattr(worker, "_context_snapshot", lambda *args, **kwargs: {
        "reference_type":"CURRENT_STATE", "active_mission":{"status":"NO_ACTIVE_MISSION"}})
    def deliver(update_id, chat_id, response):
        seen.update({"response":response,"job_id":os.environ.get("NEXUS_DURABLE_JOB_ID"),
            "correlation_id":os.environ.get("NEXUS_CORRELATION_ID"),
            "department":os.environ.get("NEXUS_DEPARTMENT"),"job_type":os.environ.get("NEXUS_JOB_TYPE")})
        return {"state":"DELIVERED"}
    monkeypatch.setattr(worker, "_deliver_response", deliver)
    monkeypatch.setattr(worker, "create_mission", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not create mission")))
    for key in ("NEXUS_DURABLE_JOB_ID","NEXUS_CORRELATION_ID","NEXUS_DEPARTMENT","NEXUS_JOB_TYPE"):
        monkeypatch.delenv(key, raising=False)
    message={"text":"What are you working on right now?"}
    assert worker._process_message_inner({"message":message},message,{"id":1288928049},
        {"id":1288928049,"username":"ray"},1288928049,1288928049,"ray",
        message["text"],590357517) is True
    assert seen == {"response":"I don't currently have an active mission.",
        "job_id":"nova-telegram-update-590357517","correlation_id":"nova-telegram-update-590357517",
        "department":"NOVA","job_type":"NOVA_TELEGRAM_STATUS_REPLY"}
    assert all(os.environ.get(key) is None for key in ("NEXUS_DURABLE_JOB_ID","NEXUS_CORRELATION_ID","NEXUS_DEPARTMENT","NEXUS_JOB_TYPE"))


def test_r23_immediate_context_fix_remains_authoritative():
    previous = {"assistant_text":"The last mission completed successfully."}
    result = resolve_context("Summarize that.", previous_turn=previous,
        long_term_memory="an unrelated historical objective")
    assert result["reference_type"] == "IMMEDIATE_REFERENT"
    assert result["resolved_referent"]["assistant_text"] == previous["assistant_text"]


def test_sequential_five_turn_mission_state_and_context_regression():
    active={"status":"NO_ACTIVE_MISSION"}
    completed={"mission_id":"done-1","objective":"Continue exact Research case",
        "status":"COMPLETE","success_verified":True,
        "success_condition":"same case reaches recommendation ready with no open questions",
        "final_outcome":"PARK recommendation persisted",
        "final_entity_state":{"entity_type":"RESEARCH_CASE","entity_id":"case-1",
            "status":"RECOMMENDATION_READY","source_count":4,"synthesis_count":2,
            "open_question_count":0,"recommendation":"PARK"},
        "historical_problem_events":[{"event_type":"MISSION_RECOVERING"}]}
    previous=None
    # 1: Greeting stays conversational (Hermes response represented as the delivered turn).
    turn=resolve_context("good evening nova",previous_turn=previous,active_mission=active,recent_completed_mission=completed)
    assert turn["reference_type"]=="GENERAL"
    previous={"user_text":"good evening nova","assistant_text":"Good evening, Ray."}
    # 2: Current-state fast path has no mission to resurrect.
    turn=resolve_context("What are you working on right now?",previous_turn=previous,
        active_mission=active,recent_completed_mission=completed)
    answer=worker._authoritative_mission_answer({"reference_type":turn["reference_type"],"active_mission":active,
        "last_completed_mission":completed})
    assert answer=="I don't currently have an active mission."
    previous={"user_text":"What are you working on right now?","assistant_text":answer}
    # 3: Immediate referent still resolves to the previous delivered answer.
    turn=resolve_context("Can you summarize that in one sentence?",previous_turn=previous,
        active_mission=active,recent_completed_mission=completed)
    assert turn["context_source"]=="PREVIOUS_ASSISTANT_TURN"
    assert turn["resolved_referent"]["assistant_text"]==answer
    previous={"user_text":"Can you summarize that in one sentence?","assistant_text":"There is no active mission."}
    # 4: The most recent verified completion is rendered from terminal evidence.
    turn=resolve_context("What was the last mission you completed?",previous_turn=previous,
        active_mission=active,recent_completed_mission=completed)
    answer=worker._authoritative_mission_answer({"reference_type":turn["reference_type"],
        "last_completed_mission":completed,"authoritative_mission_snapshot":completed})
    assert "RECOMMENDATION_READY" in answer and "PARK recommendation" in answer
    previous={"user_text":"What was the last mission you completed?","assistant_text":answer}
    # 5: Completion explanation uses that immediately named mission plus verified evidence.
    turn=resolve_context("Why was that considered complete?",previous_turn=previous,
        active_mission=active,recent_completed_mission=completed)
    answer=worker._authoritative_mission_answer({"reference_type":turn["reference_type"],
        "last_completed_mission":completed,"authoritative_mission_snapshot":completed})
    assert "success condition was independently verified" in answer
    assert "technical limit" not in answer
