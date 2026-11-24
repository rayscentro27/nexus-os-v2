from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
S1_RELEASE = Path.home() / ".nexus/releases/nexus-systems-engine-s1-20261028"
sys.path.insert(0, str(S1_RELEASE))
sys.path.insert(0, str(ROOT / "scripts/systems"))

from systems_engine_s1_batch_d.service import _install_diagnostics, _safe_install_failure


def test_failure_diagnostics_keep_exit_and_sanitized_stdout_stderr():
    result = subprocess.CompletedProcess(
        ["npm"], 1,
        stdout="npm error code ERESOLVE\nnpm error summary: peer conflict\napi_key=synthetic_secret_value",
        stderr="npm error code ERESOLVE\nAuthorization: Bearer synthetic_bearer_token_123456",
    )
    diagnostic = _install_diagnostics(result, stage="package_install", package="rea-agents",
        package_version="6.8.0", cwd=Path.home(), node_version="v24.22.1", npm_version="11.4.2")
    assert diagnostic["exit_code"] == 1
    assert diagnostic["npm_error_code"] == "ERESOLVE"
    assert "peer conflict" in diagnostic["stdout_tail"]
    assert "synthetic_secret_value" not in diagnostic["stdout_tail"]
    assert "synthetic_bearer_token_123456" not in diagnostic["stderr_tail"]
    assert diagnostic["working_directory"] == str(Path.home())
    assert diagnostic["package_version"] == "6.8.0"


def test_npm_auth_material_is_redacted():
    result = subprocess.CompletedProcess(["npm"], 1,
        stdout="", stderr="//registry.npmjs.org/:_authToken=synthetic_npm_auth_token_value")
    diagnostic = _install_diagnostics(result, stage="package_install", package="rea-agents",
        package_version="6.8.0", cwd=Path.home(), node_version=None, npm_version=None)
    assert "synthetic_npm_auth_token_value" not in diagnostic["stderr_tail"]


def test_specific_npm_error_code_is_not_collapsed_to_exit_one():
    result = subprocess.CompletedProcess(["npm"], 1,
        stdout="", stderr="npm error code ERESOLVE\nnpm error peer dependency conflict")
    assert _safe_install_failure(result, "REA_PACKAGE_INSTALL") == "REA_PACKAGE_INSTALL_ERESOLVE"


def test_install_env_uses_distinct_empty_npm_config_paths(tmp_path):
    from systems_engine_s1_batch_d.service import _safe_install_env
    user_config = tmp_path / "user.npmrc"
    global_config = tmp_path / "global.npmrc"
    user_config.write_text("")
    global_config.write_text("")
    env = _safe_install_env(tmp_path / "node", user_config=str(user_config), global_config=str(global_config))
    assert env["NPM_CONFIG_USERCONFIG"] != env["NPM_CONFIG_GLOBALCONFIG"]
    assert env["NPM_CONFIG_USERCONFIG"] == str(user_config)
    assert env["NPM_CONFIG_GLOBALCONFIG"] == str(global_config)
