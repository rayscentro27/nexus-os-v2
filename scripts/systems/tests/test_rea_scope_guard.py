from __future__ import annotations

import sys
from pathlib import Path

S1_RELEASE = Path.home() / ".nexus/releases/nexus-systems-engine-s1-20261028"
sys.path.insert(0, str(S1_RELEASE))

from systems_engine_s1_batch_d.service import _rea_setup_scope_is_exact

CONFIG = Path.home() / ".config/opencode/opencode.jsonc"


def test_informational_codex_mention_does_not_reject_opencode_plan():
    plan = {"summary": "Codex is a supported client", "target": str(CONFIG)}
    assert _rea_setup_scope_is_exact(plan, CONFIG)


def test_informational_claude_mention_does_not_reject_opencode_plan():
    plan = {"message": "Claude Code configuration is available", "target": str(CONFIG)}
    assert _rea_setup_scope_is_exact(plan, CONFIG)


def test_informational_auth_json_mention_does_not_reject_opencode_plan():
    plan = {"notes": "auth.json belongs to a separate integration", "target": str(CONFIG)}
    assert _rea_setup_scope_is_exact(plan, CONFIG)


def test_general_client_inventory_is_not_treated_as_proposed_writes():
    plan = {
        "clients": [
            {"client": {"name": "opencode", "configPath": str(CONFIG)}, "detected": True,
             "configured": False, "status": "needs_configuration"},
            {"client": {"name": "codex", "configPath": str(Path.home()/'.codex/config.toml')},
             "detected": True, "configured": False, "status": "needs_configuration"},
            {"client": {"name": "claude_code", "configPath": str(Path.home()/'.claude.json')},
             "detected": True, "configured": False, "status": "needs_configuration"},
        ],
        "summary": "Inventory only; Codex, Claude, Copilot, VS Code, Command Code, OMP and auth.json are supported.",
    }
    assert _rea_setup_scope_is_exact(plan, CONFIG)


def test_actual_proposed_codex_config_mutation_fails():
    plan = {"target": str(CONFIG), "planned_changes": [
        {"client": "codex", "path": str(Path.home()/'.codex/config.toml'), "action": "write"}]}
    assert not _rea_setup_scope_is_exact(plan, CONFIG)


def test_actual_proposed_claude_config_mutation_fails():
    plan = {"target": str(CONFIG), "planned_changes": [
        {"client": "claude_code", "path": str(Path.home()/'.claude.json'), "action": "write"}]}
    assert not _rea_setup_scope_is_exact(plan, CONFIG)


def test_actual_proposed_auth_json_mutation_fails():
    plan = {"target": str(CONFIG), "planned_changes": [
        {"client": "opencode", "path": str(Path.home()/'.config/opencode/auth.json'), "action": "write"}]}
    assert not _rea_setup_scope_is_exact(plan, CONFIG)


def test_opencode_only_planned_mutation_passes():
    plan = {"planned_changes": [
        {"client": "opencode", "path": str(CONFIG), "action": "write"}]}
    assert _rea_setup_scope_is_exact(plan, CONFIG)


def test_any_other_configuration_target_remains_prohibited():
    plan = {"planned_changes": [
        {"client": "opencode", "path": str(CONFIG), "action": "write"},
        {"client": "opencode", "path": str(Path.home()/'.config/other/client.json'), "action": "write"}]}
    assert not _rea_setup_scope_is_exact(plan, CONFIG)
