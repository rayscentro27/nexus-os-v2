import os
from pathlib import Path


ROOT = Path(os.environ.get("NOVA_DEPLOY_TEST_ROOT", Path(__file__).resolve().parents[3]))


def test_actionable_dispatch_precedes_capability_shortcut():
    semantic = (ROOT / "scripts/nova/semantic_orchestration.py").read_text()
    worker = (ROOT / "scripts/nova/nova_telegram_worker.py").read_text()
    assert semantic.index("if requested_departments and") < semantic.index('return _result("CAPABILITY_QUERY"')
    assert worker.index('if semantic.get("intent") == "MULTI_DEPARTMENT_ASSIGNMENT"') < worker.index('if semantic.get("intent") == "PRIOR_WORK_QUERY"')


def test_dispatch_uses_only_existing_governed_actions_and_alpha_scope_guard():
    adapter = (ROOT / "scripts/nova/nexus_mcp_status.py").read_text()
    assert 'call_mcp_tool("nexus_assign_research"' in adapter
    assert 'call_mcp_tool("nexus_assign_department_query"' in adapter
    assert "ALPHA_GOVERNED_ACTION_SCOPE_UNSUPPORTED" in adapter
    assert "def assign_department_tasks(" in adapter


def test_nova_does_not_gain_direct_notebooklm_or_new_work_systems():
    adapter = (ROOT / "scripts/nova/nexus_mcp_status.py").read_text()
    worker = (ROOT / "scripts/nova/nova_telegram_worker.py").read_text()
    assert '"NOTEBOOKLM"' not in adapter
    assert "notebooklm" not in worker.casefold()
    assert "scheduler" not in worker.casefold()
    assert "create_queue" not in worker.casefold()


def test_multi_department_dispatch_preserves_real_ids_and_parent_correlation():
    adapter = (ROOT / "scripts/nova/nexus_mcp_status.py").read_text()
    worker = (ROOT / "scripts/nova/nova_telegram_worker.py").read_text()
    assert '"parent_request_id": str(parent_request_id)' in adapter
    assert '"job_id": str(job_id)' in adapter
    assert "render_assignment_batch(batch, owner_objective_id)" in worker
    assert '"parent_objective_id": owner_objective_id' in worker
