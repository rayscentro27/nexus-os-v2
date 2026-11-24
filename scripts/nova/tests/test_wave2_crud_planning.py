from nova.nova_telegram_worker import _wave2_crud_plan
from nova.operator_shadow import decide_wave2_action


def test_note_crud_plan_is_ordered_exact_path_and_independently_verified():
    text = ('Create one small internal note that says "Phase 4 start,", read it, '
            'update that same note to say "Phase 4 passed,", read it again, '
            'delete that same note, verify it is gone.')
    decision = decide_wave2_action(text)
    plan, path, contents = _wave2_crud_plan(decision, text, 7654321)
    assert path == "reports/nova_internal/nova_note_7654321.md"
    assert decision["ACTION_SEQUENCE"] == ["CREATE", "READ", "UPDATE", "READ", "DELETE", "VERIFY_ABSENT"]
    assert contents == {"CREATE": "Phase 4 start,", "UPDATE": "Phase 4 passed,"}
    names = [row["capability_id"].rsplit(":", 1)[-1] for row in plan["steps"]]
    assert names == ["nexus_write_workspace_artifact", "nexus_read_workspace_file",
                     "nexus_read_workspace_file", "nexus_update_workspace_artifact",
                     "nexus_read_workspace_file", "nexus_read_workspace_file",
                     "nexus_delete_workspace_artifact", "nexus_read_workspace_file"]
    mutations = [row for row in plan["steps"] if row["capability_id"].endswith((
        "nexus_write_workspace_artifact", "nexus_update_workspace_artifact", "nexus_delete_workspace_artifact"))]
    assert all(row["arguments"]["relative_path"] == path for row in mutations)
    assert mutations[1]["arguments"]["note_id"] == path
    assert mutations[2]["arguments"]["note_id"] == path
    assert mutations[2]["verification"]["assertion"] == {"not_found": True}
    assert plan["steps"][-1]["step_id"] == "crud_8_verify_absent"
    assert plan["steps"][-1]["verification"]["assertion"] == {"not_found": True}
    assert plan["mission_success_condition"]["verification"]["assertion"] == {"not_found": True}


def test_compound_create_first_scope_ignores_prior_note_lineage(tmp_path, monkeypatch):
    from nova.operator_v1 import begin_mission
    from nova.nova_telegram_worker import _wave2_new_entity_sequence
    monkeypatch.setenv("NOVA_OPERATOR_DB", str(tmp_path / "operator.sqlite3"))
    text = ('Nova, create one small internal note that says "CRUD certification start," read it, '
            'update that same note to say "CRUD certification passed," read it again, delete that same note, '
            'verify it is gone.')
    previous = {"note_id": "reports/nova_internal/nova_note_590357529.md"}
    decision = decide_wave2_action(text, lineage=previous)
    assert decision["CREATE_NEW_ENTITY"] is True
    assert _wave2_new_entity_sequence(decision) is True
    understanding = begin_mission({"mission_id": "compound-new-entity", "update_id": 532,
        "user_id": "ray", "current_objective_lineage": previous},
        "Create a new NOTE entity; ordered action graph CREATE -> READ -> UPDATE -> READ -> DELETE -> VERIFY_ABSENT.",
        {"intent": "CREATE_NOTE"}, [])["understanding"]
    target = understanding["target_entity"]
    assert target["explicit_new_entity_request"] is True
    assert target["entity_ids"] == []
    assert target["explicit_target"] is False


def test_short_compound_natural_language_graphs_are_preserved():
    scenarios = [
        ('Create a note that says "alpha", then read it.', ["CREATE", "READ"]),
        ('Create a note that says "alpha", update it to "beta", then read it.',
         ["CREATE", "UPDATE", "READ"]),
        ('Create a note that says "alpha", read it, update it to "beta", read it, '
         'delete it, and verify it is absent.',
         ["CREATE", "READ", "UPDATE", "READ", "DELETE", "VERIFY_ABSENT"]),
    ]
    for text, expected in scenarios:
        decision = decide_wave2_action(text, lineage={"note_id": "reports/nova_internal/old.md"})
        assert decision["ACTION_SEQUENCE"] == expected
        assert decision["CREATE_NEW_ENTITY"] is True
        assert decision["ENTITY_ID"] is None
        plan, _, _ = _wave2_crud_plan(decision, text, 9001)
        assert plan["steps"][0]["capability_id"].endswith("nexus_write_workspace_artifact")


def test_resume_after_update_and_delete_does_not_repeat_create_or_mutation(tmp_path, monkeypatch):
    import hashlib
    import json
    from nova import operator_v1 as op

    monkeypatch.setenv("NOVA_OPERATOR_DB", str(tmp_path / "operator.sqlite3"))
    text = ('Create one small internal note that says "start," read it, update that same note to '
            'say "passed,", read it again, delete that same note, verify it is gone.')
    update_id = 9002
    old_lineage = {"note_id": "reports/nova_internal/old-note.md"}
    decision = decide_wave2_action(text, lineage=old_lineage)
    plan, path, _ = _wave2_crud_plan(decision, text, update_id)
    assert path == "reports/nova_internal/nova_note_9002.md"
    mission_id = "nova_compound_recovery"
    mission = {"mission_id": mission_id, "operator_mission_id": mission_id, "update_id": update_id,
               "user_id": "ray"}
    operator_text = ("Create a new NOTE entity; ordered action graph CREATE -> READ -> UPDATE -> READ "
                     "-> DELETE -> VERIFY_ABSENT. Original request: " + text)
    catalog = [
        {"capability_id": "mcp:nexus_mcp_remote:nexus_write_workspace_artifact", "tool_name": "nexus_write_workspace_artifact",
         "source_id": "nexus_mcp_remote", "read_write_class": "WRITE", "authorized": True,
         "input_schema": {"type": "object", "required": ["relative_path", "content"], "properties": {
             "relative_path": {"type": "string"}, "content": {"type": "string"}}}},
        {"capability_id": "mcp:nexus_mcp_remote:nexus_read_workspace_file", "tool_name": "nexus_read_workspace_file",
         "source_id": "nexus_mcp_remote", "read_write_class": "READ", "authorized": True,
         "input_schema": {"type": "object", "required": ["relative_path"], "properties": {
             "relative_path": {"type": "string"}}}},
        {"capability_id": "mcp:nexus_mcp_remote:nexus_update_workspace_artifact", "tool_name": "nexus_update_workspace_artifact",
         "source_id": "nexus_mcp_remote", "read_write_class": "WRITE", "authorized": True,
         "input_schema": {"type": "object", "required": ["relative_path", "note_id", "content", "expected_sha256"], "properties": {
             "relative_path": {"type": "string"}, "note_id": {"type": "string"},
             "content": {"type": "string"}, "expected_sha256": {"type": "string"}}}},
        {"capability_id": "mcp:nexus_mcp_remote:nexus_delete_workspace_artifact", "tool_name": "nexus_delete_workspace_artifact",
         "source_id": "nexus_mcp_remote", "read_write_class": "WRITE", "authorized": True,
         "input_schema": {"type": "object", "required": ["relative_path", "note_id", "expected_sha256"], "properties": {
             "relative_path": {"type": "string"}, "note_id": {"type": "string"},
             "expected_sha256": {"type": "string"}}}},
    ]
    state = {}
    counters = {"create": 0, "update": 0, "delete": 0, "read": 0}
    failure = {"passed_reads": 0, "after_update_reads": 0, "after_delete_reads": 0}

    def executor(cap, args, _owner):
        tool = cap["tool_name"]
        if tool == "nexus_write_workspace_artifact":
            counters["create"] += 1
            assert args["relative_path"] == path and path not in state
            state[path] = args["content"]
            return {"call_succeeded": True, "result_data": {"status": "created", "path": path,
                "content": state[path], "sha256": hashlib.sha256(state[path].encode()).hexdigest()}}
        if tool == "nexus_update_workspace_artifact":
            counters["update"] += 1
            digest = hashlib.sha256(state[path].encode()).hexdigest()
            assert args["relative_path"] == path and args["note_id"] == path and args["expected_sha256"] == digest
            state[path] = args["content"]
            return {"call_succeeded": True, "result_data": {"status": "updated", "path": path,
                "content": state[path], "previous_sha256": digest,
                "sha256": hashlib.sha256(state[path].encode()).hexdigest()}}
        if tool == "nexus_delete_workspace_artifact":
            counters["delete"] += 1
            digest = hashlib.sha256(state[path].encode()).hexdigest()
            assert args["relative_path"] == path and args["note_id"] == path and args["expected_sha256"] == digest
            del state[path]
            return {"call_succeeded": True, "result_data": {"status": "deleted", "deleted": True,
                "path": path, "previous_sha256": digest}}
        counters["read"] += 1
        if state:
            data = {"status": "ok", "path": path, "content": state[path],
                    "sha256": hashlib.sha256(state[path].encode()).hexdigest()}
            # Fail only after the preceding mutation is fully verified, at the
            # explicit later READ or VERIFY_ABSENT step.
            if state[path] == "passed,":
                if failure["passed_reads"] == 0:
                    failure["passed_reads"] += 1  # UPDATE postcondition succeeds.
                elif failure["after_update_reads"] < 2:
                    failure["after_update_reads"] += 1
                    return {"call_succeeded": False, "error_code": "INJECTED_READ_RETRY"}
        else:
            data = {"status": "not_found", "error": "workspace_file_not_found"}
            if counters["delete"] and failure["after_delete_reads"] < 2:
                failure["after_delete_reads"] += 1
                return {"call_succeeded": False, "error_code": "INJECTED_ABSENCE_READ_RETRY"}
        return {"call_succeeded": True, "result_data": data}

    planner = lambda _prompt: json.dumps(plan)
    first = op.run_objective(mission, operator_text, {"intent": "CREATE_NOTE"}, owner_authorized=True,
        planner=planner, catalog=catalog, executor=executor, max_replans=1)
    assert first["status"] == "RECOVERING"
    assert counters["create"] == 1
    assert counters["update"] == 1
    assert counters["delete"] == 0
    assert failure["after_update_reads"] == 2
    # Resume from the persisted update; the failed read is retried against the
    # same entity. Then force uncertainty after DELETE's real side effect.
    second = op.run_objective(mission, operator_text, {"intent": "CREATE_NOTE"}, owner_authorized=True,
        planner=planner, catalog=catalog, executor=executor, max_replans=0)
    assert second["status"] == "RECOVERING"
    assert counters["create"] == 1
    assert counters["update"] == 1
    assert counters["delete"] == 1
    # The failed delete verifier retained its successful mutation result.
    # Resume by reading the same path, never by repeating the delete.
    third = op.run_objective(mission, operator_text, {"intent": "CREATE_NOTE"}, owner_authorized=True,
        planner=planner, catalog=catalog, executor=executor, max_replans=0)
    assert third["status"] == "COMPLETE"
    assert counters["create"] == 1
    assert counters["update"] == 1
    assert counters["delete"] == 1
    assert path not in state


def test_file_create_uses_bounded_internal_path_and_file_identity():
    text = 'Create a text file named report.txt that says "ready".'
    decision = decide_wave2_action(text)
    plan, path, _ = _wave2_crud_plan(decision, text, 1234)
    assert path == "reports/nova_internal/report.txt"
    assert plan["steps"][0]["arguments"]["relative_path"] == path


def test_delete_completion_envelope_uses_persisted_predelete_hash():
    from nova.nova_telegram_worker import _wave2_result_envelope
    digest = "a" * 64
    result = _wave2_result_envelope({"ENTITY_TYPE": "NOTE", "ACTION_CLASS": "DELETE",
        "ENTITY_ID": "reports/nova_internal/exact.md"}, {
        "status": "COMPLETE", "mission_id": "same-mission", "entities": {},
        "final_result": {"mission_success_verified": True, "all_postconditions_verified": True,
            "mission_success_evidence": {"status": "PASS", "verified_at": "now"},
            "completed_steps": [{"capability_id": "mcp:nexus:nexus_delete_workspace_artifact",
                "result": {"result_data": {"previous_sha256": digest}}}]},
    })
    assert result["ACTION_SUCCEEDED"] is True
    assert result["ENTITY_ID"] == "reports/nova_internal/exact.md"
    assert result["CURRENT_VERSION_OR_HASH"] == digest


def _lineage_rows(op, mission_id):
    with op._connect() as db:
        return [dict(row) for row in db.execute(
            "SELECT entity_type,entity_id,entity_role,created_by_step,metadata_json "
            "FROM operator_lineage WHERE mission_id=? ORDER BY entity_type", (mission_id,))]


def test_note_lineage_is_one_logical_entity_through_crud(tmp_path, monkeypatch):
    import json
    from nova import operator_v1 as op

    monkeypatch.setenv("NOVA_OPERATOR_DB", str(tmp_path / "operator.sqlite3"))
    mission = op.begin_mission({"mission_id": "note-lineage", "update_id": 7101, "user_id": "ray"},
        "Create a NOTE, update the same NOTE, then delete it.", {"intent": "CREATE_NOTE"}, [])
    path = "reports/nova_internal/nova_note_7101.md"
    for i, action in enumerate(("create", "read", "update", "delete"), 1):
        op._store_lineage(mission["mission_id"], {
            "persisted_step_id": f"note-lineage:{i}:{action}", "goal": f"{action.title()} the same NOTE",
            "inputs": {"relative_path": path}},
            {"source": "workspace", "result_data": {"path": path, "status": action}})
        rows = _lineage_rows(op, mission["mission_id"])
        assert [(row["entity_type"], row["entity_role"]) for row in rows] == [("NOTE", "CURRENT_OBJECT")]
        assert rows[0]["entity_id"] == path
        metadata = json.loads(rows[0]["metadata_json"])
        assert metadata["logical_entity_type"] == "NOTE"
        assert metadata["storage_backing_type"] == "FILE"
        assert metadata["storage_path"] == path
    assert rows[0]["created_by_step"] == "note-lineage:4:delete"


def test_file_lineage_remains_file_and_not_note(tmp_path, monkeypatch):
    from nova import operator_v1 as op

    monkeypatch.setenv("NOVA_OPERATOR_DB", str(tmp_path / "operator.sqlite3"))
    mission = op.begin_mission({"mission_id": "file-lineage", "update_id": 7102, "user_id": "ray"},
        "Create a FILE and read it.", {"intent": "CREATE_FILE"}, [])
    path = "reports/nova_internal/report.txt"
    op._store_lineage(mission["mission_id"], {"persisted_step_id": "file-lineage:1:create",
        "goal": "Create exactly one bounded FILE", "inputs": {"relative_path": path}},
        {"source": "workspace", "result_data": {"path": path, "status": "created"}})
    rows = _lineage_rows(op, mission["mission_id"])
    assert [(row["entity_type"], row["entity_id"], row["entity_role"]) for row in rows] == [
        ("FILE", path, "CURRENT_OBJECT")]


def test_note_reconciles_old_file_current_lineage_as_storage_backing(tmp_path, monkeypatch):
    import json
    from nova import operator_v1 as op

    monkeypatch.setenv("NOVA_OPERATOR_DB", str(tmp_path / "operator.sqlite3"))
    mission = op.begin_mission({"mission_id": "note-backing", "update_id": 7103, "user_id": "ray"},
        "Create a NOTE backed by a workspace file.", {"intent": "CREATE_NOTE"}, [])
    path = "reports/nova_internal/nova_note_7103.md"
    op._store_lineage(mission["mission_id"], {"persisted_step_id": "note-backing:1:old",
        "goal": "Create a FILE", "inputs": {"relative_path": path}},
        {"source": "workspace", "result_data": {"path": path, "status": "created"}})
    op._store_lineage(mission["mission_id"], {"persisted_step_id": "note-backing:2:note",
        "goal": "Read the same NOTE", "inputs": {"relative_path": path}},
        {"source": "workspace", "result_data": {"path": path, "status": "ok"}})
    rows = _lineage_rows(op, mission["mission_id"])
    assert {(row["entity_type"], row["entity_role"]) for row in rows} == {
        ("NOTE", "CURRENT_OBJECT"), ("FILE", "STORAGE_BACKING")}
    backing = next(row for row in rows if row["entity_type"] == "FILE")
    metadata = json.loads(backing["metadata_json"])
    assert metadata["relationship"] == "STORAGE_BACKING_FOR"
    assert metadata["logical_entity_type"] == "NOTE"
    assert metadata["reconciled_from_role"] == "CURRENT_OBJECT"


def test_note_response_extraction_does_not_emit_file_alias():
    from nova import operator_v1 as op

    path = "reports/nova_internal/nova_note_response.md"
    assert op._extract_entities({"path": path}, logical_entity_type="NOTE") == {"note_id": path}
    assert op._extract_entities({"path": path}, logical_entity_type="FILE") == {"file_id": path}
    rendered = op._render_result({"mission_success_evidence": {"result": {"result_data": {"path": path}}},
        "completed_steps": [{"goal": "Create a bounded NOTE", "result": {"result_data": {"path": path}}}]},
        logical_entity_type="NOTE")
    assert f"NOTE_ID={path}" in rendered
    assert "FILE_ID=" not in rendered


def test_storage_backing_lineage_is_not_used_as_current_entity(tmp_path, monkeypatch):
    from nova import operator_v1 as op

    monkeypatch.setenv("NOVA_OPERATOR_DB", str(tmp_path / "operator.sqlite3"))
    mission = op.begin_mission({"mission_id": "backing-lookup", "update_id": 7104, "user_id": "ray"},
        "Create a note.", {"intent": "CREATE_NOTE"}, [])
    path = "reports/nova_internal/nova_note_7104.md"
    op._store_lineage(mission["mission_id"], {"persisted_step_id": "backing-lookup:1:file",
        "goal": "Create a bounded FILE", "inputs": {"relative_path": path}},
        {"source": "workspace", "result_data": {"path": path}})
    op._store_lineage(mission["mission_id"], {"persisted_step_id": "backing-lookup:2:note",
        "goal": "Read the same NOTE", "inputs": {"relative_path": path}},
        {"source": "workspace", "result_data": {"path": path}})
    assert op.mission_for_entity("ray", [path]) == mission["mission_id"]
