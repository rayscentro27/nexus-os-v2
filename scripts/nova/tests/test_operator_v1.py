import json
from pathlib import Path
import hashlib

import pytest

from nova import operator_v1 as op


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("NOVA_OPERATOR_DB", str(tmp_path / "operator.sqlite3"))
    return tmp_path


def capability(cap_id, *, source="mcp-one", name="tool", rw="READ", schema=None):
    return {
        "capability_id": cap_id, "source_type": "MCP", "source_id": source,
        "server_id": source, "server_or_department": source, "tool_name": name,
        "name": name, "description": name, "input_schema": schema or {"type": "object"},
        "read_write_class": rw, "cost_class": "ZERO", "consequence_class": "SANDBOX",
        "approval_class": "ALLOW", "reversible": True, "authorized": True,
        "runtime_health": "PASS", "write_allowed": True,
        "external_effect": False, "production_effect": False,
        "server_metadata": {"route_mode": "HERMES_APPROVED_MCP", "sandbox_only": True},
    }


def mission(mid="nova_test_1", update=1001, owner="ray"):
    return {"mission_id": mid, "update_id": update, "user_id": owner,
            "objective_text": "test objective", "correlation_id": "corr-test"}


def step(step_id, goal, cap_id, args=None, verify=None, deps=None):
    return {"step_id": step_id, "goal": goal, "capability_id": cap_id,
            "arguments": args or {}, "depends_on": deps or [],
            "expected_postcondition": goal, "verification": verify,
            "alternate_capability_ids": []}


def plan_json(steps, gap=None, mission_success=None):
    result = {"steps": steps, "capability_gap": gap}
    if mission_success is not None:
        result["mission_success_condition"] = mission_success
    return json.dumps(result)


def success(cap_id, arguments=None, assertion=None, description="Requested outcome is present"):
    return {"description": description, "verification": {"capability_id": cap_id,
        "arguments": arguments or {}, "assertion": assertion or {"exists": ""}}}


def test_a_generic_mcp_create_read_update_read_delete_postconditions(store):
    catalog = [
        capability("mcp:canary:create", source="canary", name="canary_create_note", rw="WRITE",
                   schema={"type": "object", "required": ["name", "content"]}),
        capability("mcp:canary:read", source="canary", name="canary_read_note", rw="READ",
                   schema={"type": "object", "required": ["NOTE_ID"]}),
        capability("mcp:canary:update", source="canary", name="canary_update_note", rw="WRITE",
                   schema={"type": "object", "required": ["NOTE_ID", "content"]}),
        capability("mcp:canary:delete", source="canary", name="canary_delete_note", rw="WRITE",
                   schema={"type": "object", "required": ["NOTE_ID"]}),
    ]
    state = {}
    calls = []

    def execute(cap, args, owner):
        name = cap["tool_name"]
        calls.append(name)
        if name == "canary_create_note":
            state["note-1"] = {"note_id": "note-1", "name": args["name"], "content": args["content"]}
            return {"call_succeeded": True, "resource_id": "note-1", "result_data": state["note-1"]}
        if name == "canary_read_note":
            note = state.get(args["NOTE_ID"])
            return ({"call_succeeded": True, "result_data": note} if note else
                    {"call_succeeded": False, "error_code": "NOTE_NOT_FOUND", "result_data": {"error": "NOTE_NOT_FOUND"}})
        if name == "canary_update_note":
            state[args["NOTE_ID"]]["content"] = args["content"]
            return {"call_succeeded": True, "result_data": state[args["NOTE_ID"]]}
        if name == "canary_delete_note":
            state.pop(args["NOTE_ID"], None)
            return {"call_succeeded": True, "result_data": {"deleted": True}}
        raise AssertionError(name)

    steps = [
        step("create", "create note", "mcp:canary:create", {"name": "ray-test", "content": "Nova can write."},
             {"capability_id": "mcp:canary:read", "arguments": {"NOTE_ID": "{{step1.result_data.note_id}}"},
              "assertion": {"contains": "Nova can write."}}),
        step("read", "read note", "mcp:canary:read", {"NOTE_ID": "{{step1.result_data.note_id}}"}),
        step("update", "update note", "mcp:canary:update", {"NOTE_ID": "{{step1.result_data.note_id}}", "content": "Nova can update."},
             {"capability_id": "mcp:canary:read", "arguments": {"NOTE_ID": "{{step1.result_data.note_id}}"},
              "assertion": {"contains": "Nova can update."}}),
        step("read-updated", "read updated note", "mcp:canary:read", {"NOTE_ID": "{{step1.result_data.note_id}}"}),
        step("delete", "delete note", "mcp:canary:delete", {"NOTE_ID": "{{step1.result_data.note_id}}"},
             {"capability_id": "mcp:canary:read", "arguments": {"NOTE_ID": "{{step1.result_data.note_id}}"},
              "assertion": {"not_found": True}}),
    ]
    mission_success = success("mcp:canary:read", {"NOTE_ID": "note-1"}, {"not_found": True},
                              "The requested delete is verified by absence of this exact note")
    result = op.run_objective(mission(), "create, read, update, read, delete note", {"intent": "APPROVED_MCP_ACTION"},
        owner_authorized=True, planner=lambda _: plan_json(steps, mission_success=mission_success), catalog=catalog, executor=execute)
    assert result["status"] == "COMPLETE"
    assert result["final_result"]["all_postconditions_verified"] is True
    assert calls == ["canary_create_note", "canary_read_note", "canary_read_note",
                     "canary_update_note", "canary_read_note", "canary_read_note", "canary_delete_note",
                     "canary_read_note", "canary_read_note"]
    status = op.status_read("nova_test_1")
    assert status["status"] == "COMPLETE"
    assert status["entity_lineage"][0]["entity_id"] == "note-1"


def test_planner_catalog_adds_related_read_capability_for_write_verification():
    write = capability("mcp:canary:create", source="canary", name="canary_create_note", rw="WRITE")
    read = capability("mcp:canary:read", source="canary", name="canary_read_note", rw="READ")
    candidates, _ = op._planner_catalog_view(
        [write, read], "create a note and verify it exists", {}, limit=1
    )
    assert [row["capability_id"] for row in candidates] == [
        "mcp:canary:create", "mcp:canary:read"
    ]


def test_b_research_failure_replans_same_mission_and_preserves_lineage(store):
    catalog = [capability("mcp:nexus:inspect", source="nexus", name="nexus_get_durable_jobs"),
               capability("mcp:nexus:broken", source="nexus", name="nexus_assign_research", rw="WRITE"),
               capability("mcp:nexus:healthy", source="nexus", name="nexus_assign_research_recovered", rw="WRITE"),
               capability("mcp:nexus:read", source="nexus", name="nexus_get_job_status", rw="READ")]
    planner_calls = []

    def planner(_):
        planner_calls.append(True)
        if len(planner_calls) == 1:
            return plan_json([step("inspect", "inspect existing job", "mcp:nexus:inspect"),
                step("assign", "assign research", "mcp:nexus:broken", {},
                    {"capability_id": "mcp:nexus:read", "arguments": {"job_id": "job-existing"},
                     "assertion": {"contains": "RUNNING"}}, ["inspect"])], mission_success=success(
                         "mcp:nexus:read", {"job_id": "job-existing"},
                         {"equals": {"path": "state", "value": "RUNNING"}}))
        return plan_json([step("inspect", "inspect existing job", "mcp:nexus:inspect"),
            step("assign-recovered", "assign same research objective", "mcp:nexus:healthy", {},
            {"capability_id": "mcp:nexus:read", "arguments": {"job_id": "{{step1.result_data.job_id}}"},
             "assertion": {"contains": "job-existing"}}, ["inspect"])], mission_success=success(
                 "mcp:nexus:read", {"job_id": "job-existing"},
                 {"equals": {"path": "state", "value": "RUNNING"}}))

    inspect_calls = []

    def execute(cap, args, owner):
        if cap["tool_name"] == "nexus_get_durable_jobs":
            inspect_calls.append(True)
            return {"call_succeeded": True, "result_data": {"job_id": "job-existing", "state": "READY"}}
        if cap["tool_name"] == "nexus_assign_research":
            raise RuntimeError("worker route temporarily unavailable")
        if cap["tool_name"] == "nexus_assign_research_recovered":
            return {"call_succeeded": True, "resource_id": "job-existing", "result_data": {"job_id": "job-existing"}}
        return {"call_succeeded": True, "result_data": {"job_id": "job-existing", "state": "RUNNING"}}

    result = op.run_objective(mission("same-op-mission"), "create Research work", {"intent": "RESEARCH_MISSION"},
        owner_authorized=True, planner=planner, catalog=catalog, executor=execute)
    assert result["status"] == "COMPLETE"
    assert result["mission_id"] == "same-op-mission"
    assert len(planner_calls) == 2
    assert len(inspect_calls) == 1
    assert op.mission_for_entity("ray", ["job-existing"]) == "same-op-mission"


def test_c_systems_inspect_repair_reverify(store):
    catalog = [capability("mcp:nexus:inspect", source="nexus", name="nexus_get_system_health"),
               capability("mcp:nexus:repair", source="nexus", name="nexus_repair_internal_worker", rw="WRITE"),
               capability("mcp:nexus:verify", source="nexus", name="nexus_get_system_health_after_repair")]
    state = {"healthy": False}

    def execute(cap, args, owner):
        if cap["tool_name"] == "nexus_get_system_health":
            return {"call_succeeded": True, "result_data": {"worker": "DOWN" if not state["healthy"] else "UP"}}
        if cap["tool_name"] == "nexus_repair_internal_worker":
            state["healthy"] = True
            return {"call_succeeded": True, "result_data": {"repair": "applied"}}
        return {"call_succeeded": True, "result_data": {"worker": "UP"}}

    steps = [step("inspect", "inspect worker", "mcp:nexus:inspect"),
             step("repair", "apply bounded internal repair", "mcp:nexus:repair", {},
                  {"capability_id": "mcp:nexus:verify", "arguments": {}, "assertion": {"contains": "UP"}}, ["inspect"])]
    result = op.run_objective(mission("systems-test"), "inspect and repair internal worker", {"intent": "DEPARTMENT_ASSIGNMENT"},
        owner_authorized=True, planner=lambda _: plan_json(steps, mission_success=success(
            "mcp:nexus:verify", {}, {"contains": "UP"})), catalog=catalog, executor=execute)
    assert result["status"] == "COMPLETE"
    assert state["healthy"]


def test_d_file_artifact_readback_verifies_without_receipt(store, tmp_path):
    target = tmp_path / "artifact.txt"
    catalog = [capability("mcp:files:write", source="files", name="workspace_write", rw="WRITE"),
               capability("mcp:files:read", source="files", name="workspace_read")]

    def execute(cap, args, owner):
        if cap["tool_name"] == "workspace_write":
            target.write_text(args["content"])
            return {"call_succeeded": True, "result_data": {"path": str(target)}}
        return {"call_succeeded": target.exists(), "result_data": {"content": target.read_text() if target.exists() else None}}

    steps = [step("write", "write bounded artifact", "mcp:files:write", {"content": "operator v1"},
        {"capability_id": "mcp:files:read", "arguments": {}, "assertion": {"contains": "operator v1"}})]
    result = op.run_objective(mission("file-test"), "write a small internal artifact", {"intent": "FILE_OR_DOCUMENT_ACTION"},
        owner_authorized=True, planner=lambda _: plan_json(steps, mission_success=success(
            "mcp:files:read", {}, {"contains": "operator v1"})), catalog=catalog, executor=execute)
    assert result["status"] == "COMPLETE"
    assert target.read_text() == "operator v1"


def test_e_multi_source_step_results_feed_following_capability(store):
    catalog = [capability("mcp:web:search", source="web", name="public_search"),
               capability("mcp:nexus:save", source="nexus", name="nexus_write_workspace_artifact", rw="WRITE"),
               capability("mcp:nexus:read", source="nexus", name="nexus_read_workspace_file")]
    saved = {}

    def execute(cap, args, owner):
        if cap["source_id"] == "web":
            return {"call_succeeded": True, "result_data": {"summary": "verified fact", "source": "example"}}
        if cap["tool_name"] == "nexus_write_workspace_artifact":
            saved["content"] = args["content"]
            return {"call_succeeded": True, "result_data": {"artifact_id": "artifact-1"}}
        return {"call_succeeded": True, "result_data": {"content": saved.get("content")}}

    steps = [step("search", "find source", "mcp:web:search"),
             step("save", "save result to Nexus artifact", "mcp:nexus:save",
                  {"content": "{{step1.result_data.summary}}"},
                  {"capability_id": "mcp:nexus:read", "arguments": {}, "assertion": {"contains": "verified fact"}}, ["search"])]
    result = op.run_objective(mission("multi-test"), "research then save to Nexus", {"intent": "ACTIONABLE"},
        owner_authorized=True, planner=lambda _: plan_json(steps, mission_success=success(
            "mcp:nexus:read", {}, {"contains": "verified fact"})), catalog=catalog, executor=execute)
    assert result["status"] == "COMPLETE"
    assert saved["content"] == "verified fact"


def test_live_catalog_normalizes_approved_server_and_tool_identity():
    row = op._catalog_row(
        {"server_id": "nova-action-canary", "server_name": "Action Canary", "approved": True,
         "route_mode": "HERMES_APPROVED_MCP", "sandbox_only": True, "runtime_health": "PASS",
         "production_effect": False, "external_effect": False, "reversible": True, "cost_class": "ZERO"},
        {"server_id": "nova-action-canary", "name": "canary_create_note", "description": "create note",
         "input_schema": {"type": "object"}, "approved": True, "read_write_class": "WRITE",
         "write_allowed": True, "cost_class": "ZERO", "external_effect": False,
         "production_effect": False, "reversible": True, "metadata_complete": True})
    assert row["capability_id"] == "mcp:nova-action-canary:canary_create_note"
    assert row["source_id"] == "nova-action-canary"
    assert row["authorized"] is True and row["runtime_health"] == "PASS"


def test_result_normalization_preserves_original_and_lowercase_entity_fields():
    value = op._normalize_result_data({"NOTE_ID": "note-1", "META": {"UPDATED_AT": "now"}})
    assert value["note_id"] == value["NOTE_ID"] == "note-1"
    assert value["meta"]["updated_at"] == value["meta"]["UPDATED_AT"] == "now"
    assert op._extract_resource(value) == "note-1"
    assert op._extract_entities(value)["note_id"] == "note-1"


def test_operator_status_read_does_not_create_or_mutate_state(store):
    path = store / "operator.sqlite3"
    assert not path.exists()
    assert op.status_read("missing") is None
    assert not path.exists()


def test_capability_gap_builds_immutable_declarative_adapter_and_resumes_same_mission(store, tmp_path, monkeypatch):
    releases = tmp_path / "cap-releases"
    registry = tmp_path / "generated.json"
    monkeypatch.setenv("NOVA_OPERATOR_GENERATED_REGISTRY", str(registry))
    monkeypatch.setenv("NOVA_OPERATOR_CAPABILITY_RELEASE_ROOT", str(releases))
    proposal = {"capability_id": "operator_reverse_text", "name": "operator_reverse_text",
        "purpose": "Reverse a supplied text string.", "operation": "reverse_text",
        "input_schema": {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}}},
        "output_schema": {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}}},
        "cost_class": "ZERO", "consequence_class": "INTERNAL", "read_write_class": "READ",
        "required_permissions": [], "dependencies": [], "tests": [
            {"input": {"text": "stressed"}, "expected": {"text": "desserts"}}]}
    calls = []
    original = op.build_and_register_capability
    def planner(prompt):
        calls.append(prompt)
        if len(calls) == 1:
            return plan_json([], {"required_capability": "reverse supplied text", "reason": "No current adapter."})[:-1] + "," + json.dumps({"capability_proposal": proposal})[1:]
        cap = "generated:operator_reverse_text"
        return plan_json([step("reverse", "reverse the text", cap, {"text": "stressed"},
            {"capability_id": cap, "arguments": {"text": "stressed"},
             "assertion": {"equals": {"path": "text", "value": "desserts"}}})], mission_success=success(
                 cap, {"text": "stressed"}, {"equals": {"path": "text", "value": "desserts"}}))
    def build(mission_id, spec):
        return original(mission_id, spec, release_root=releases, registry_path=registry)
    monkeypatch.setattr(op, "build_and_register_capability", build)
    result = op.run_objective(mission("cap-build-mission"), "reverse the word stressed",
        {"intent": "ACTIONABLE"}, owner_authorized=True, planner=planner, catalog=[], max_replans=2)
    assert result["status"] == "COMPLETE"
    assert result["mission_id"] == "cap-build-mission"
    rows = json.loads(registry.read_text())
    record = rows[0]
    release = Path(record["release_path"])
    assert record["manifest_valid"] is True
    assert hashlib.sha256((release / "RELEASE_MANIFEST.json").read_bytes()).hexdigest() == record["manifest_hash"]
    assert not (release / "capability.json").stat().st_mode & 0o222


def test_case_target_retains_exact_linked_reads_and_same_project_continuation():
    target = {"entity_type": "RESEARCH_CASE", "entity_ids": ["case-1"], "explicit_target": True,
              "related_entity_ids": {"case_id": "case-1", "objective_id": "obj-1",
                                     "project_id": "project-1", "job_id": "job-1"}}
    state = capability("state", name="nexus_get_research_state",
        schema={"type": "object", "properties": {"objective_id": {"type": "string"}}})
    jobs = capability("jobs", name="nexus_get_durable_jobs",
        schema={"type": "object", "properties": {"job_id": {"type": "string"}}})
    continuation = capability("continue", name="nexus_continue_research", rw="WRITE",
        schema={"type": "object", "required": ["objective_id", "project_id", "job_id"],
                "properties": {"objective_id": {"type": "string"}, "project_id": {"type": "string"},
                               "job_id": {"type": "string"}}})
    unrelated = capability("other-jobs", name="nexus_get_durable_jobs",
        schema={"type": "object", "properties": {"job_id": {"type": "string"}}})
    assert op.entity_action_compatible(target, state, "continue this case")
    assert op.entity_action_compatible(target, jobs, "continue this case")
    assert op.entity_action_compatible(target, continuation, "continue this case")
    assert op._arguments_bind_target(target, continuation,
        {"objective_id": "obj-1", "project_id": "project-1", "job_id": "job-1"})
    assert not op._arguments_bind_target(target, continuation,
        {"objective_id": "obj-1", "project_id": "project-1", "job_id": "unrelated-job"})
    # A supporting read can help gather evidence; it cannot verify this case.
    workspace_read = capability("file", name="nexus_read_workspace_file",
        schema={"type": "object", "properties": {"relative_path": {"type": "string"}}})
    assert op.entity_action_compatible(target, workspace_read, "inspect release history", support_read=True)
    assert not op.entity_action_compatible(target, workspace_read, "inspect release history")


def test_capability_gap_replans_and_uses_linked_alternate_before_returning(store):
    current = mission("same-case-gap-replan")
    current["current_objective_lineage"] = {"case_id": "case-1", "objective_id": "obj-1",
        "project_id": "project-1", "job_id": "job-1"}
    state = capability("mcp:nexus:jobs", source="nexus", name="nexus_get_durable_jobs",
        schema={"type": "object", "properties": {"job_id": {"type": "string"}}})
    calls = []
    def planner(_):
        calls.append(True)
        if len(calls) == 1:
            return plan_json([], {"required_capability": "worker failure evidence", "reason": "Initial selection missed linked tools."})
        return plan_json([step("inspect", "inspect the exact linked job", state["capability_id"],
            {"job_id": "job-1"})], mission_success=success(state["capability_id"], {"job_id": "job-1"},
                {"equals": {"path": "job_id", "value": "job-1"}}))
    def execute(cap, args, owner):
        assert args == {"job_id": "job-1"}
        return {"call_succeeded": True, "result_data": {"job_id": "job-1", "state": "BLOCKED"}}
    result = op.run_objective(current, "continue that same Research case and inspect the original failure",
        {"intent": "CONTINUE_EXISTING_WORK"}, owner_authorized=True, planner=planner,
        catalog=[state], executor=execute)
    assert result["status"] == "COMPLETE"
    assert result["mission_id"] == "same-case-gap-replan"
    assert len(calls) == 2
    with op._connect() as db:
        events = [row[0] for row in db.execute(
            "select event_type from operator_events where mission_id=?", ("same-case-gap-replan",))]
    assert "CAPABILITY_ACQUISITION_PLANNING" in events


def test_capability_gap_refreshes_live_catalog_and_resumes_same_mission(store, monkeypatch):
    available = capability("mcp:nexus:execution-trace", source="nexus",
        name="nexus_get_research_execution_trace",
        schema={"type": "object", "required": ["job_id"],
                "properties": {"job_id": {"type": "string"}}})
    discoveries = [[], [available]]
    def discover_catalog(*, force=True):
        assert force is True
        return discoveries.pop(0) if discoveries else [available]
    monkeypatch.setattr(op, "discover_catalog", discover_catalog)
    plans = []
    def planner(prompt):
        plans.append(prompt)
        if len(plans) == 1:
            return plan_json([], {"required_capability": "exact worker execution trace",
                                  "reason": "The bounded initial catalog omitted the exact trace tool."})
        assert "mcp:nexus:execution-trace" in prompt
        cap_id = available["capability_id"]
        return plan_json([step("trace", "read the exact existing job trace", cap_id,
            {"job_id": "job_existing_1"})], mission_success=success(cap_id,
            {"job_id": "job_existing_1"}, {"equals": {"path": "job_id", "value": "job_existing_1"}}))
    def execute(cap, args, owner):
        assert cap["tool_name"] == "nexus_get_research_execution_trace"
        assert args == {"job_id": "job_existing_1"}
        return {"call_succeeded": True, "result_data": {"job_id": "job_existing_1", "events": ["retained"]}}
    current = mission("same-live-gap-mission")
    current["current_objective_lineage"] = {"objective_id": "obj-1", "project_id": "project-1",
        "job_id": "job_existing_1", "case_id": "case-1"}
    result = op.run_objective(current, "continue the exact same Research case",
        {"intent": "CONTINUE_EXISTING_WORK"}, owner_authorized=True, planner=planner,
        executor=execute, max_replans=2)
    assert result["status"] == "COMPLETE"
    assert result["mission_id"] == "same-live-gap-mission"
    assert len(plans) == 2
    with op._connect() as db:
        events = [row[0] for row in db.execute(
            "select event_type from operator_events where mission_id=?", ("same-live-gap-mission",))]
    assert "CAPABILITY_ACQUISITION_LIVE_CATALOG_REFRESHED" in events
    assert "CAPABILITY_GAP_EVALUATED" in events


def test_capability_build_failure_replans_repairs_and_resumes(store, tmp_path, monkeypatch):
    releases, registry = tmp_path / "releases", tmp_path / "registry.json"
    monkeypatch.setenv("NOVA_OPERATOR_GENERATED_REGISTRY", str(registry))
    monkeypatch.setenv("NOVA_OPERATOR_CAPABILITY_RELEASE_ROOT", str(releases))
    proposal = {"capability_id": "operator_reverse_retry", "name": "operator_reverse_retry",
        "purpose": "Reverse supplied text.", "operation": "reverse_text",
        "input_schema": {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}}},
        "output_schema": {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}}},
        "cost_class": "ZERO", "consequence_class": "INTERNAL", "read_write_class": "READ",
        "required_permissions": [], "dependencies": [],
        "tests": [{"input": {"text": "abc"}, "expected": {"text": "cba"}}]}
    original = op.build_and_register_capability
    attempts, plans = [], []
    def build(mid, spec):
        attempts.append(True)
        if len(attempts) == 1:
            raise ValueError("TRANSIENT_ISOLATED_BUILD_FAILURE")
        return original(mid, spec, release_root=releases, registry_path=registry)
    def planner(_):
        plans.append(True)
        if len(plans) <= 2:
            return json.dumps({"steps": [], "capability_gap": {"required_capability": "reverse", "reason": "missing"},
                              "capability_proposal": proposal})
        cap_id = "generated:operator_reverse_retry"
        return plan_json([step("reverse", "reverse text", cap_id, {"text": "abc"})],
            mission_success=success(cap_id, {"text": "abc"}, {"equals": {"path": "text", "value": "cba"}}))
    monkeypatch.setattr(op, "build_and_register_capability", build)
    result = op.run_objective(mission("cap-build-retry"), "reverse abc", {"intent": "ACTIONABLE"},
        owner_authorized=True, planner=planner, catalog=[])
    assert result["status"] == "COMPLETE"
    assert len(attempts) == 2 and len(plans) == 3


def test_capability_security_expansion_waits_for_approval(store):
    proposal = {"capability_id": "operator_needs_scope", "name": "operator_needs_scope",
        "purpose": "An operation requiring additional authority.", "operation": "reverse_text",
        "input_schema": {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}}},
        "output_schema": {"type": "object", "properties": {"text": {"type": "string"}}},
        "cost_class": "ZERO", "consequence_class": "INTERNAL", "read_write_class": "READ",
        "required_permissions": ["security_scope_expansion"], "dependencies": [],
        "tests": [{"input": {"text": "a"}, "expected": {"text": "a"}}]}
    def planner(_):
        return json.dumps({"steps": [], "capability_gap": {"required_capability": "scoped read",
            "reason": "Requires a security scope."}, "capability_proposal": proposal})
    result = op.run_objective(mission("cap-security-boundary"), "perform scoped read",
        {"intent": "ACTIONABLE"}, owner_authorized=True, planner=planner, catalog=[])
    assert result["status"] == "WAITING_FOR_APPROVAL"
    assert "permission" in result["boundary"]["exact_requirement"].casefold()


def test_unresolved_gap_replans_before_true_blocker_and_never_returns_capability_gap(store):
    plans = []
    def planner(_):
        plans.append(True)
        return plan_json([], {"required_capability": "missing internal capability",
                              "reason": "No compatible read or builder is available.",
                              "capability_proposal_applicable": False})
    result = op.run_objective(mission("cap-gap-exhaustion"), "perform safe internal inspection",
        {"intent": "ACTIONABLE"}, owner_authorized=True, planner=planner, catalog=[])
    assert len(plans) == 3
    assert result["status"] == "RECOVERING"
    assert result["status"] != "CAPABILITY_GAP"
    with op._connect() as db:
        rows = db.execute("select event_type,payload_json from operator_events where mission_id=?",
                          ("cap-gap-exhaustion",)).fetchall()
    assert any(row[0] == "CAPABILITY_ACQUISITION_PLANNING" for row in rows)
    empty_plan_events = [json.loads(row[1]) for row in rows if row[0] == "EMPTY_PLAN_RECOVERY"]
    assert len(empty_plan_events) == 3
    assert all(row["same_mission"] and row["missing_action_classified"] for row in empty_plan_events)


def test_self_repair_uses_immutable_test_scope_release_and_retries_step(store, tmp_path):
    root = tmp_path / "fixture"
    root.mkdir()
    source = root / "config.txt"
    source.write_text("mode=broken\n")
    out = op.self_repair_release_flow(target_root=root, relative_path="config.txt",
        expected_before="mode=broken", replacement="mode=healthy",
        validation=lambda p: "mode=healthy" in p.read_text(),
        original_step=lambda p: "mode=healthy" in p.read_text(), test_scope=True)
    assert all(out[k] is True for k in ("failure_detected", "diagnosis_created", "patch_built", "tests_pass",
        "immutable_release_created", "manifest_valid", "test_scope_release_promoted", "original_step_retried", "postcondition_pass"))
    assert (root / ".nova_operator_releases" / "ACTIVE_RELEASE").read_text().strip() == out["release_id"]
    assert source.read_text() == "mode=broken\n"
    with pytest.raises(PermissionError, match="SELF_REPAIR_ROOT_NOT_APPROVED"):
        op.self_repair_release_flow(target_root=root, relative_path="config.txt", expected_before="mode=broken",
            replacement="mode=healthy", validation=lambda p: True, original_step=lambda p: True)


def test_self_repair_failed_original_step_rolls_back_test_pointer(store, tmp_path):
    root = tmp_path / "fixture-rollback"
    root.mkdir()
    (root / "config.txt").write_text("mode=broken\n")
    releases = root / ".nova_operator_releases"
    releases.mkdir()
    (releases / "ACTIVE_RELEASE").write_text("previous-release\n")
    with pytest.raises(RuntimeError, match="SELF_REPAIR_ORIGINAL_STEP_RETRY_FAILED"):
        op.self_repair_release_flow(target_root=root, relative_path="config.txt", expected_before="mode=broken",
            replacement="mode=healthy", validation=lambda p: "healthy" in p.read_text(),
            original_step=lambda p: False, test_scope=True)
    assert (releases / "ACTIVE_RELEASE").read_text() == "previous-release\n"


def test_operator_status_native_tool_is_visible_and_read_only(store):
    catalog = [op._operator_status_capability()]
    result = op.run_objective(mission("status-target"), "status check", {"intent": "ACTIONABLE"},
        owner_authorized=True, planner=lambda _: plan_json([step("status", "read mission status",
            "nova:operator:nexus_get_operator_mission_status", {"mission_id": "status-target"})],
            mission_success=success("nova:operator:nexus_get_operator_mission_status",
                {"mission_id": "status-target"}, {"equals": {"path": "mission_id", "value": "status-target"}})),
        catalog=catalog)
    assert result["status"] == "COMPLETE"
    assert result["final_result"]["completed_steps"][0]["result"]["result_data"]["mission_id"] == "status-target"
    assert result["final_result"]["completed_steps"][0]["result"]["result_data"]["no_mutation"] is True


def test_mission_completion_requires_independent_success_postcondition(store):
    read = capability("mcp:nexus:research_state", source="nexus", name="nexus_get_research_state")
    calls = []
    def execute(cap, args, owner):
        calls.append(cap["tool_name"])
        return {"call_succeeded": True, "result_data": {"queue": {"ready": 1}, "job": {"state": "READY"}}}
    condition = success("mcp:nexus:research_state", {},
        {"equals": {"path": "job.state", "value": "RUNNING"}},
        "The exact target Research job is running")
    result = op.run_objective(mission("diagnostic-does-not-finish"),
        "continue the existing Research job until running", {"intent": "RESEARCH_MISSION"},
        owner_authorized=True, planner=lambda _: plan_json([
            step("inspect", "read Research state", "mcp:nexus:research_state")], mission_success=condition),
        catalog=[read], executor=execute, max_replans=0)
    assert calls == ["nexus_get_research_state", "nexus_get_research_state"]
    assert result["status"] == "RECOVERING"
    assert op.status_read("diagnostic-does-not-finish")["status"] == "RECOVERING"


def test_completion_consistency_regressions():
    failed = {"status": "FAIL"}
    passed = {"status": "PASS"}
    # 1. Successful diagnostic read without requested state change.
    assert not op.completion_guard(mission_success_verified=False, mission_success_evidence=failed)
    # 2. All plan steps can finish while the final objective condition remains false.
    assert not op.completion_guard(mission_success_verified=False, mission_success_evidence=failed)
    # 3. Independent mission-level evidence permits completion.
    assert op.completion_guard(mission_success_verified=True, mission_success_evidence=passed)
    # 4. A human/approval boundary remains nonterminal completion.
    assert not op.completion_guard(mission_success_verified=False, mission_success_evidence=failed)
    # 5. Contradictory "complete" plus pending language is rejected.
    assert not op.completion_guard(mission_success_verified=True, mission_success_evidence=passed,
        response="Objective complete, but the mission remains active pending running state.")
    # 6. Tool success is insufficient when independent verification fails.
    assert not op.completion_guard(mission_success_verified=False, mission_success_evidence=failed)
    # 7. A missing receipt does not prevent completion when independent state proves success.
    assert op.completion_guard(mission_success_verified=True,
        mission_success_evidence={"status": "PASS", "receipt_id": None, "verified_by": "readback"})


def test_action_not_available_and_true_blocker_require_complete_evidence():
    assert op.action_not_available_allowed({"live_catalog_checked": True}) is False
    complete = {key: True for key in ("live_catalog_checked", "explicit_target_checked", "primary_path_evaluated",
        "primary_path_attempted_when_reasonable", "alternate_mcp_evaluated", "alternate_nexus_action_evaluated",
        "alternate_department_evaluated", "safe_repair_evaluated", "capability_acquisition_evaluated",
        "postcondition_verification_evaluated")}
    assert op.action_not_available_allowed(complete) is True
    assert not op.true_blocker_allowed("TRUE_TECHNICAL_BLOCKER", {})
    exhausted = {
        "blocker_evidence_source": "NOVA_RUNTIME_EVALUATOR",
        "reasonable_paths_exhausted": True, "internal_repair_exhausted": True,
        "capability_acquisition_not_possible_or_requires_approval": True,
        "existing_approved_direct_capability_evaluated": True,
        "existing_approved_alternate_capability_evaluated": True,
        "safe_adapter_reroute_evaluated": True,
        "safe_schema_lineage_repair_evaluated": True,
        "bounded_capability_acquisition_evaluated": True,
        "postcondition_based_recovery_evaluated": True,
        "same_entity_continuation_evaluated": True,
    }
    assert not op.true_blocker_allowed("TRUE_TECHNICAL_BLOCKER", {
        **exhausted, "bounded_capability_acquisition_evaluated": False})
    assert op.true_blocker_allowed("TRUE_TECHNICAL_BLOCKER", exhausted)


def test_workspace_crud_family_preflight_requires_all_live_approved_tools():
    rows = []
    tools = {
        "nexus_write_workspace_artifact": ({"relative_path", "content"}, "WRITE"),
        "nexus_read_workspace_file": ({"relative_path"}, "READ"),
        "nexus_update_workspace_artifact": ({"relative_path", "content", "expected_sha256"}, "WRITE"),
        "nexus_delete_workspace_artifact": ({"relative_path", "expected_sha256"}, "WRITE"),
    }
    for name, (required, rw) in tools.items():
        rows.append(capability(f"mcp:nexus_mcp_remote:{name}", source="nexus_mcp_remote",
            name=name, rw=rw, schema={"type": "object", "required": sorted(required),
            "properties": {key: {"type": "string"} for key in required}}))
    assert op.workspace_crud_family_preflight(rows)["status"] == "PASS"
    assert op.workspace_crud_family_preflight(rows[:-1])["status"] == "FAIL"


def test_actionable_understands_general_operator_status_followups():
    for text in ("what are you working on?", "what is the status of that?", "what step are you on?",
                 "why are you stuck?", "what happens next?", "did that finish?"):
        assert op.actionable(text)


def test_cross_turn_lineage_bundle_is_exact_and_complete(store):
    op.begin_mission(mission("lineage-parent", update=100, owner="ray"),
        "create target objects", {"intent": "ACTIONABLE"}, [])
    with op._connect() as db:
        for kind, ident in (("OBJECTIVE", "obj-exact"), ("PROJECT", "project-exact"),
                            ("JOB", "job-exact"), ("CASE", "case-exact")):
            db.execute("INSERT INTO operator_lineage VALUES(?,?,?,?,?,?,?)",
                ("lineage-parent", kind, ident, "CURRENT_OBJECT", "step-create", "2026-10-19T12:00:00Z",
                 json.dumps({"source": "test"})))
    lineage = op.current_entity_lineage("ray")
    assert lineage["objective_id"] == "obj-exact"
    assert lineage["project_id"] == "project-exact"
    assert lineage["job_id"] == "job-exact"
    assert lineage["case_id"] == "case-exact"
    assert lineage["case_entity"]["mission_id"] == "lineage-parent"
    assert op.mission_for_entity("ray", [lineage["case_id"]]) == "lineage-parent"


def test_begin_mission_binds_referred_case_from_durable_lineage(store):
    target = mission("lineage-followup", update=101, owner="ray")
    target["current_objective_lineage"] = {
        "objective_id": "obj-exact", "project_id": "project-exact",
        "job_id": "job-exact", "case_id": "case-exact",
    }
    result = op.begin_mission(target, "Continue the Research case you just opened.",
        {"intent": "CROSS_DEPARTMENT_CONTINUATION", "department": "RESEARCH"}, [])
    assert result["understanding"]["target_entity"]["entity_ids"] == ["case-exact"]
    assert result["understanding"]["target_entity"]["entity_type"] == "RESEARCH_CASE"
    assert result["understanding"]["target_entity"]["lineage_source"] == "DURABLE_CURRENT_ENTITY_LINEAGE"


def test_untyped_mutation_reference_binds_exact_current_note(store):
    target = mission("lineage-delete-note", update=102, owner="ray")
    target["current_objective_lineage"] = {"note_id": "note-exact"}
    result = op.begin_mission(target, "delete it", {"intent": "ACTIONABLE"}, [])
    assert result["understanding"]["target_entity"]["entity_ids"] == ["note-exact"]
    assert result["understanding"]["target_entity"]["lineage_source"] == "DURABLE_CURRENT_ENTITY_LINEAGE"


def test_exact_case_lineage_wins_when_generic_research_status_is_unknown(store):
    target = mission("exact-case-precedence", update=103, owner="ray")
    target["current_objective_lineage"] = {"objective_id": "obj-current", "case_id": "case-current"}
    result = op.begin_mission(target, "continue the case you just opened", {"intent": "RESEARCH_MISSION"}, [])
    understanding = result["understanding"]
    assert understanding["target_entity"]["entity_ids"] == ["case-current"]
    assert understanding["target_entity"]["entity_type"] == "RESEARCH_CASE"
    assert "generic status" not in understanding["desired_outcome"].casefold()


@pytest.mark.parametrize("entity_type,entity_id,schema,name,expected", [
    ("RESEARCH_CASE", "case-1", {"type": "object", "properties": {"case_id": {"type": "string"}}}, "nexus_continue_research_case", True),
    ("RESEARCH_CASE", "case-1", {"type": "object", "properties": {"project_id": {"type": "string"}, "job_id": {"type": "string"}}}, "nexus_continue_research", False),
    ("RESEARCH_JOB", "job-1", {"type": "object", "properties": {"job_id": {"type": "string"}}}, "nexus_recover_research_job", True),
    ("NOTE", "note-1", {"type": "object", "properties": {"note_id": {"type": "string"}}}, "canary_update_note", True),
    ("FILE", "file-1", {"type": "object", "properties": {"relative_path": {"type": "string"}}}, "nexus_update_file", True),
    ("RESEARCH_PROJECT", "project-1", {"type": "object", "properties": {"project_id": {"type": "string"}}}, "nexus_continue_research", True),
])
def test_existing_entity_constrains_capability_schema(entity_type, entity_id, schema, name, expected):
    target = {"entity_type": entity_type, "entity_ids": [entity_id], "explicit_target": True}
    cap = capability("cap", name=name, schema=schema, rw="WRITE")
    assert op.entity_action_compatible(target, cap, "continue that existing entity") is expected


def test_explicit_request_for_another_entity_allows_create_capability():
    target = {"entity_type": "RESEARCH_CASE", "entity_ids": ["case-1"], "explicit_target": True}
    cap = capability("assign", name="nexus_assign_research", rw="WRITE",
                     schema={"type": "object", "properties": {"objective": {"type": "string"}}})
    assert op.entity_action_compatible(target, cap, "create another Research project") is True


def test_save_plan_rejects_assignment_that_replaces_exact_case(store):
    current = mission("case-route-guard", update=901, owner="ray")
    current["current_objective_lineage"] = {"case_id": "case-1", "project_id": "project-1"}
    op.begin_mission(current, "Nova, keep working on that same Research case.",
        {"intent": "CONTINUE_EXISTING_WORK"}, [])
    catalog = [
        capability("assign", name="nexus_assign_research", rw="WRITE",
                   schema={"type": "object", "properties": {"objective": {"type": "string"}}}),
        capability("read", name="nexus_get_research_state", schema={"type": "object",
                   "properties": {"objective_id": {"type": "string"}}}),
    ]
    plan = {"steps": [{"step_id": "wrong", "goal": "continue the case", "capability_id": "assign",
            "arguments": {"objective": "continue the case"}}],
        "mission_success_condition": {"description": "same case advances",
            "verification": {"capability_id": "read", "arguments": {}, "assertion": {"equals": {"path": "case_id", "value": "case-1"}}}}}
    with pytest.raises(ValueError, match="ENTITY_ACTION_CAPABILITY_MISMATCH"):
        op.save_plan("case-route-guard", plan, catalog)


def test_live_planner_catalog_keeps_only_exact_entity_compatible_tools():
    catalog = [
        capability("project", name="nexus_continue_research", rw="WRITE",
                   schema={"type": "object", "properties": {"project_id": {"type": "string"}, "job_id": {"type": "string"}}}),
        capability("case", name="nexus_continue_research_case", rw="WRITE",
                   schema={"type": "object", "properties": {"case_id": {"type": "string"}}}),
        capability("assign", name="nexus_assign_research", rw="WRITE",
                   schema={"type": "object", "properties": {"objective": {"type": "string"}}}),
    ]
    target = {"entity_type": "RESEARCH_CASE", "entity_ids": ["case-1"], "explicit_target": True}
    candidates, _ = op._planner_catalog_view(catalog, "continue that same Research case", target)
    assert [row["capability_id"] for row in candidates] == ["case"]


def test_completion_renderer_does_not_echo_historical_pending_plan_text():
    response = op._render_result({
        "mission_success_evidence": {"status": "PASS", "result": {"result_data": {
            "data": {"jobs": [{"job_id": "job-exact"}], "research_work_item": {"case_id": "case-exact"}}
        }}},
        "completed_steps": [{"goal": "Keep the parent mission active pending verified running state.",
            "result": {"result_data": {"work_id": "work-exact"}}}],
    })
    assert "Objective complete" in response
    assert "pending" not in response.casefold()
    assert "JOB_ID=job-exact" in response
    assert "CASE_ID=case-exact" in response
    assert "WORK_ID=work-exact" in response
    assert "PROJECT_ID=work-exact" not in response


def test_default_planner_allows_bounded_recovery_plan_to_finish(monkeypatch):
    from nexus_agent_platform.bridge import oracle_hermes_cli

    observed = {}

    def fake_run(prompt, session, **kwargs):
        observed.update(session=session, **kwargs)
        return type("Result", (), {"status": "SUCCEEDED", "response": "{}", "error": None})()

    monkeypatch.setattr(oracle_hermes_cli, "run_oracle_hermes", fake_run)
    result = op._default_planner("plan prompt", "mission-123", "request-456")
    first_session = observed["session"]
    op._default_planner("next plan prompt", "mission-123", "request-789")

    assert result == "{}"
    assert observed["timeout_seconds"] == 120
    assert observed["request_id"] == "mission-123"
    assert observed["structured_task"] is True
    assert observed["session"] != first_session


def test_resuming_legacy_mission_persists_normalized_related_lineage(store):
    current = mission("legacy-lineage-refresh", update=901, owner="ray")
    current["current_objective_lineage"] = {
        "case_id": "case-exact", "objective_id": "objective-exact",
        "project_id": "project-exact", "job_id": "job-exact",
    }
    catalog = [capability("state", name="nexus_get_research_state", schema={
        "type": "object", "properties": {"objective_id": {"type": "string"}},
    })]
    op.begin_mission(current, "Continue the same Research case", {"intent": "CONTINUE_EXISTING_WORK"}, catalog)

    with op._connect() as db:
        row = db.execute("SELECT understanding_json FROM operator_missions WHERE mission_id=?",
                         ("legacy-lineage-refresh",)).fetchone()
        old = json.loads(row["understanding_json"])
        target = old["target_entity"]
        target["linked_entity_ids"] = target.pop("related_entity_ids")
        db.execute("UPDATE operator_missions SET understanding_json=? WHERE mission_id=?",
                   (json.dumps(old), "legacy-lineage-refresh"))

    op.begin_mission(current, "Continue the same Research case", {"intent": "CONTINUE_EXISTING_WORK"}, catalog)
    with op._connect() as db:
        refreshed = json.loads(db.execute("SELECT understanding_json FROM operator_missions WHERE mission_id=?",
                                          ("legacy-lineage-refresh",)).fetchone()[0])
    assert refreshed["target_entity"]["related_entity_ids"]["case_id"] == "case-exact"
    assert refreshed["target_entity"]["related_entity_ids"]["objective_id"] == "objective-exact"

    plan = {"steps": [{"step_id": "inspect", "goal": "Read exact objective state",
            "capability_id": "state", "arguments": {"objective_id": "objective-exact"},
            "expected_postcondition": "Exact state was read"}],
        "mission_success_condition": {"description": "Same case has a verified result",
            "verification": {"capability_id": "state", "arguments": {"objective_id": "objective-exact"},
                "assertion": {"contains": "RESEARCH_COMPLETE"}}}}
    assert len(op.save_plan("legacy-lineage-refresh", plan, catalog)) == 1


def test_planner_catalog_preserves_enum_contracts():
    catalog = [capability("prior", name="nexus_get_prior_department_result", schema={
        "type": "object", "properties": {"department": {"type": "string",
        "enum": ["RESEARCH", "ALPHA", "SYSTEMS"]}},
    })]
    candidates, _ = op._planner_catalog_view(catalog, "read prior department result", {})
    assert candidates[0]["input_schema"]["properties"]["department"]["enum"] == [
        "RESEARCH", "ALPHA", "SYSTEMS"
    ]


def test_argument_validation_enforces_enum_without_jsonschema(monkeypatch):
    import sys
    monkeypatch.setitem(sys.modules, "jsonschema", None)
    schema = {"type": "object", "required": ["department"], "properties": {
        "department": {"type": "string", "enum": ["RESEARCH", "ALPHA", "SYSTEMS"]},
    }}
    op._validate_args(schema, {"department": "RESEARCH"})
    with pytest.raises(ValueError, match="INPUT_SCHEMA_INVALID"):
        op._validate_args(schema, {"department": "Research"})


def test_workspace_postcondition_path_reference_falls_back_to_validated_step_input():
    path = "reports/nova_internal/nova_note_590357529.md"
    schema = {"type": "object", "required": ["relative_path", "content"], "properties": {
        "relative_path": {"type": "string"}, "content": {"type": "string"},
    }}
    arguments = {"relative_path": path, "content": "Phase 4 live test,"}
    op._validate_args(schema, arguments)

    # A conflict/compact receipt can omit the path even though the write used it.
    result = {"call_succeeded": True, "result_data": {"status": "conflict"}}
    preserved = op._preserve_workspace_path_reference(result, arguments)
    resolved = op._resolve_refs({"relative_path": "{{step1.relative_path}}"}, {"step1": preserved})
    assert resolved == {"relative_path": path}

    adapter_path = "reports/nova_internal/nova_note_adapter-returned.md"
    returned = op._preserve_workspace_path_reference({"relative_path": adapter_path}, arguments)
    assert returned["relative_path"] == adapter_path

    # Malformed caller input remains rejected before an adapter can execute.
    for invalid in (None, {"path": path}, [path], 7):
        with pytest.raises(ValueError, match="INPUT_SCHEMA_INVALID"):
            op._validate_args(schema, {"relative_path": invalid, "content": "Phase 4 live test,"})


def test_workspace_write_retry_verifies_existing_same_note_by_validated_path(store):
    path = "reports/nova_internal/nova_note_590357529.md"
    write_id = "mcp:nexus_mcp_remote:nexus_write_workspace_artifact"
    read_id = "mcp:nexus_mcp_remote:nexus_read_workspace_file"
    catalog = [
        capability(write_id, source="nexus_mcp_remote", name="nexus_write_workspace_artifact", rw="WRITE",
            schema={"type": "object", "required": ["relative_path", "content"], "properties": {
                "relative_path": {"type": "string"}, "content": {"type": "string"}}}),
        capability(read_id, source="nexus_mcp_remote", name="nexus_read_workspace_file", rw="READ",
            schema={"type": "object", "required": ["relative_path"], "properties": {
                "relative_path": {"type": "string"}}}),
    ]
    mid = "nova_existing_note_recovery"
    op.begin_mission(mission(mid), "Create the internal note", {"intent": "CREATE_NOTE"}, catalog)
    action = {"persisted_step_id": mid + ":1:step1", "selected_capability_id": write_id,
        "sequence": 1, "inputs": {"relative_path": path, "content": "Phase 4 live test,"},
        "expected_postcondition": {"description": "same path matches", "verification": {
            "capability_id": read_id, "arguments": {"relative_path": "{{step1.relative_path}}"},
            "assertion": {"equals": {"path": "content", "value": "Phase 4 live test,"}}}},
        "alternate_capability_ids": []}
    calls = []

    def executor(cap, arguments, _owner_authorized):
        calls.append((cap["capability_id"], dict(arguments)))
        if cap["capability_id"] == write_id:
            return {"call_succeeded": True, "result_data": {"status": "conflict",
                "created": False, "error": "refusing_to_overwrite_existing_artifact"}}
        return {"call_succeeded": True, "result_data": {"status": "ok", "path": path,
            "content": "Phase 4 live test,"}}

    result, error = op._execute_one(mid, action, {row["capability_id"]: row for row in catalog}, {},
                                    owner_authorized=True, executor=executor)
    assert error is None
    assert result["postcondition"]["status"] == "PASS"
    assert calls == [(write_id, {"relative_path": path, "content": "Phase 4 live test,"}),
                     (read_id, {"relative_path": path})]


def test_existing_note_update_does_not_retry_create_or_replace_entity(store):
    path = "reports/nova_internal/nova_note_590357529.md"
    original = "Phase 4 live test,"
    updated = "Phase 4 live test passed,"
    read_id = "mcp:nexus_mcp_remote:nexus_read_workspace_file"
    update_id = "mcp:nexus_mcp_remote:nexus_update_workspace_artifact"
    create_id = "mcp:nexus_mcp_remote:nexus_write_workspace_artifact"
    catalog = [
        capability(read_id, source="nexus_mcp_remote", name="nexus_read_workspace_file", rw="READ",
            schema={"type": "object", "required": ["relative_path"], "properties": {
                "relative_path": {"type": "string"}}}),
        capability(update_id, source="nexus_mcp_remote", name="nexus_update_workspace_artifact", rw="WRITE",
            schema={"type": "object", "required": ["relative_path", "expected_sha256", "content"], "properties": {
                "relative_path": {"type": "string"}, "expected_sha256": {"type": "string"},
                "content": {"type": "string"}, "note_id": {"type": "string"}}}),
        capability(create_id, source="nexus_mcp_remote", name="nexus_write_workspace_artifact", rw="WRITE"),
    ]
    state = {"content": original}
    state["sha256"] = hashlib.sha256(original.encode()).hexdigest()
    calls = []
    current = mission("same-existing-note-mission")
    current["current_objective_lineage"] = {"note_id": path, "file_id": path, "mission_id": current["mission_id"]}

    def execute(cap, args, _owner_authorized):
        calls.append((cap["capability_id"], dict(args)))
        if cap["capability_id"] == read_id:
            return {"call_succeeded": True, "result_data": {"path": path, **state}}
        if cap["capability_id"] == update_id:
            assert args["relative_path"] == path and args["note_id"] == path
            if args["expected_sha256"] != state["sha256"]:
                return {"call_succeeded": True, "result_data": {"status": "conflict", "updated": False}}
            state["content"] = args["content"]
            state["sha256"] = hashlib.sha256(state["content"].encode()).hexdigest()
            return {"call_succeeded": True, "result_data": {"path": path, "status": "updated",
                "updated": True, "created": False, "sha256": state["sha256"]}}
        raise AssertionError("CREATE must not be retried for an existing exact entity")

    steps = [
        step("read-existing", "read the exact existing NOTE", read_id, {"relative_path": path}),
        step("update-same", "update the same existing NOTE", update_id,
            {"relative_path": path, "note_id": path, "expected_sha256": "{{step1.result_data.sha256}}",
             "content": updated},
            {"capability_id": read_id, "arguments": {"relative_path": path},
             "assertion": {"equals": {"path": "content", "value": updated}}}, ["step1"]),
    ]
    condition = success(read_id, {"relative_path": path},
        {"equals": {"path": "content", "value": updated}},
        "The same NOTE path contains the requested updated content")
    result = op.run_objective(current, "Update that same note to the requested content",
        {"intent": "MODIFY_EXISTING_OBJECTIVE"}, owner_authorized=True,
        planner=lambda _: plan_json(steps, mission_success=condition), catalog=catalog,
        executor=execute)
    assert result["status"] == "COMPLETE"
    assert result["mission_id"] == "same-existing-note-mission"
    assert state["content"] == updated
    assert [cap_id for cap_id, _ in calls].count(create_id) == 0
    assert [cap_id for cap_id, _ in calls].count(update_id) == 1
    assert calls[1][1]["relative_path"] == path
    assert calls[1][1]["note_id"] == path
    assert op.mission_for_entity("ray", [path]) == "same-existing-note-mission"


def test_planner_recovery_context_compacts_large_results_and_gap_catalog():
    result = {"call_succeeded": True, "result_data": {"status": "PARTIAL", "data": {
        "jobs": [{"job_id": "job-exact", "state": "BLOCKED", "last_error_code": "WORKER_FAILED",
                  "last_error_summary": "RESEARCH_EXIT_1: stderr empty"}],
        "research_work_item": {"case_id": "case-exact", "status": "FAILED_RETRYABLE",
                               "result": "x" * 10000},
        "unrelated_payload": {"text": "discard" * 1000},
    }}}
    completed = op._compact_planner_completed([{"step_id": "step-1", "goal": "Inspect exact job",
        "capability_id": "job-read", "status": "COMPLETE", "result": result}])
    prior = op._compact_planner_prior({"capability_gap": {"reason": "No path", "catalog_capability_ids": [
        f"tool-{i}" for i in range(1000)], "planner_gap": {"description": "Needs exact case continuation"}}})
    serialized = json.dumps({"completed": completed, "prior": prior})
    assert "job-exact" in serialized and "WORKER_FAILED" in serialized
    assert "case-exact" in serialized and "Needs exact case continuation" in serialized
    assert "catalog_capability_ids" not in serialized
    assert len(serialized) < 5000


def test_exact_entity_continuation_action_survives_planner_candidate_limit():
    target = {"entity_type": "RESEARCH_CASE", "entity_ids": ["case-exact"],
        "explicit_target": True, "related_entity_ids": {"case_id": "case-exact",
        "objective_id": "objective-exact", "project_id": "project-exact", "job_id": "job-exact"}}
    distractors = [capability(f"read-{i}", name=f"nexus_get_misc_state_{i}", schema={
        "type": "object", "properties": {"objective_id": {"type": "string"}},
    }) for i in range(15)]
    continuation = capability("continue", name="nexus_continue_research", rw="WRITE", schema={
        "type": "object", "properties": {key: {"type": "string"} for key in
            ("objective_id", "project_id", "job_id", "instruction")},
        "required": ["objective_id", "project_id", "job_id", "instruction"],
    })
    assignment = capability("assign", name="nexus_assign_research", rw="WRITE", schema={
        "type": "object", "properties": {"objective": {"type": "string"}},
    })
    candidates, _ = op._planner_catalog_view(distractors + [assignment, continuation],
        "continue exact case", target, limit=6)
    ids = [row["capability_id"] for row in candidates]
    assert "continue" in ids
    assert "assign" not in ids
    assert len(ids) <= 6


def test_exact_entity_planner_excludes_unbound_read_surfaces():
    target = {"entity_type": "RESEARCH_CASE", "entity_ids": ["case-exact"],
        "explicit_target": True, "related_entity_ids": {"case_id": "case-exact",
        "objective_id": "objective-exact", "project_id": "project-exact", "job_id": "job-exact"}}
    continuation = capability("continue", source="nexus", name="nexus_continue_research", rw="WRITE", schema={
        "type": "object", "properties": {key: {"type": "string"} for key in
            ("objective_id", "project_id", "job_id", "instruction")},
    })
    exact_read = capability("case-read", source="nexus", name="nexus_get_research_case", rw="READ",
        schema={"type": "object", "properties": {"case_id": {"type": "string"}}})
    generic_google = capability("gmail", source="google", name="gmail_search", rw="READ",
        schema={"type": "object", "properties": {"query": {"type": "string"}}})
    candidates, _ = op._planner_catalog_view([generic_google, continuation, exact_read],
        "continue this exact case", target)
    ids = {row["capability_id"] for row in candidates}
    assert ids == {"continue", "case-read"}


def test_planner_does_not_repeat_desired_outcome_in_input():
    outcome = "Continue this exact existing mission through verified completion."
    captured = {}
    mission_data = {"mission_id": "compact-plan", "objective_text": "Original objective",
                    "current_instruction": outcome}
    understanding = {"desired_outcome": outcome, "success_condition": "verified completion",
                     "target_entity": {}}
    op.plan_objective(mission_data, understanding, [],
        planner=lambda prompt: (captured.update(prompt=prompt) or json.dumps({"steps": []})))
    assert captured["prompt"].count(outcome) == 1

