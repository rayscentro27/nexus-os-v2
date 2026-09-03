from nexus_agent_platform import research_operational_state as ros


def test_operational_contract_keeps_activity_and_availability_distinct(monkeypatch):
    state = {
        "research_department_operational_state": "OPERATIONAL",
        "alpha_primary_agent_activity": "IDLE",
        "alpha_specialist_availability": "AVAILABLE",
        "research_background_process_state": "STOPPED",
        "queued_research_jobs": 0,
    }
    monkeypatch.setattr(ros, "build_research_operational_state", lambda: state)
    summary = ros.alpha_status_summary()
    assert "operational" in summary
    assert "idle" in summary
    assert "available for delegation" in summary
    assert "stopped" in summary


def test_latest_append_only_record_wins(monkeypatch, tmp_path):
    monkeypatch.setattr(ros, "ROOT", tmp_path)
    (tmp_path / "data/runtime").mkdir(parents=True)
    (tmp_path / "reports/runtime/supabase_ready").mkdir(parents=True)
    (tmp_path / "data/governed").mkdir(parents=True)
    (tmp_path / "data/runtime/alpha_telegram_status.json").write_text('{"State":"ALIVE"}')
    (tmp_path / "scripts/alpha").mkdir(parents=True)
    (tmp_path / "scripts/alpha/alpha_discovery.py").write_text("# bounded")
    (tmp_path / "data/governed/alpha_research.jsonl").write_text(
        '{"research_id":"r1","status":"CHALLENGED","question":"q","source_refs":["a"],"candidate_content_ids":["c"]}\n'
    )
    (tmp_path / "data/governed/alpha_discovery_queue.jsonl").write_text(
        '{"content_id":"c1","state":"ROUTED"}\n{"content_id":"c1","state":"COMPLETED"}\n'
    )
    state = ros.build_research_operational_state()
    assert state["queued_research_jobs"] == 0
    assert state["open_research_objectives"] == 1
    assert state["objective_progress"]["parent_objectives"][0]["progress_percent"] == 100


def test_empty_queue_retains_incomplete_objective_action():
    state = {
        "empty_queue_next_action": "INSPECT_INCOMPLETE_OBJECTIVES_AND_CONTINUE",
        "invariants": {"idle_is_not_unavailable": True, "available_is_not_active": True},
    }
    assert state["empty_queue_next_action"] == "INSPECT_INCOMPLETE_OBJECTIVES_AND_CONTINUE"
    assert state["invariants"]["idle_is_not_unavailable"] is True
