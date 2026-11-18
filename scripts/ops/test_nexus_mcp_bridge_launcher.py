from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from build_nexus_mcp_release import bind_launchd_to_release


ROOT = Path(__file__).resolve().parents[2]
LAUNCHER = ROOT / "scripts/ops/nexus_mcp_bridge.sh"


def test_packaged_release_launcher_self_binds_and_uses_its_runtime_root(tmp_path: Path) -> None:
    release = tmp_path / "nexus-capability-actions-fixture-r99"
    launcher = release / "scripts/ops/nexus_mcp_bridge.sh"
    launcher.parent.mkdir(parents=True)
    shutil.copy2(LAUNCHER, launcher)

    env = dict(os.environ, NEXUS_MCP_LAUNCHER_ROOT_ONLY="1")
    resolved = subprocess.check_output(["/bin/zsh", str(launcher)], env=env, text=True).strip()
    assert Path(resolved) == release.resolve()

    text = launcher.read_text(encoding="utf-8")
    assert "nexus-capability-actions-20261020-r20" not in text
    assert "nexus-capability-actions-20261020-r21" not in text
    assert 'ROOT="$(cd "$SCRIPT_DIR/../.." && pwd -P)"' in text
    assert 'export PYTHONPATH="$ROOT:$ROOT/scripts"' in text
    assert 'export NEXUS_REPO_ROOT="$CANONICAL"' in text
    assert 'export NEXUS_RESEARCH_STATE_ROOT="${NEXUS_RESEARCH_STATE_ROOT:-$CANONICAL/data}"' in text
    assert 'cd "$ROOT"' in text


def test_worker_environment_keeps_release_imports_ahead_of_canonical_fallback() -> None:
    wrapper = (ROOT / "scripts/ops/run_with_canonical_runtime_env.sh").read_text(encoding="utf-8")
    assert 'export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$NEXUS_CANONICAL_ROOT/scripts"' in wrapper
    assert 'export PYTHONPATH="$NEXUS_CANONICAL_ROOT/scripts${PYTHONPATH:+:$PYTHONPATH}"' not in wrapper


def test_release_packager_rebinds_launchd_metadata_to_new_release(tmp_path: Path) -> None:
    release = tmp_path / "candidate"
    plist = release / "launchd/com.nexus.nexus-mcp-bridge.plist"
    plist.parent.mkdir(parents=True)
    plist.write_text(
        "<string>/Users/raymonddavis/.nexus/releases/"
        "nexus-capability-actions-20261020-r20/scripts/ops/nexus_mcp_bridge.sh</string>\n"
        "<string>/Users/raymonddavis/.nexus/releases/"
        "nexus-capability-actions-20261020-r20</string>\n",
        encoding="utf-8",
    )
    target = Path.home() / ".nexus/releases/nexus-capability-actions-20261021-r22"
    assert bind_launchd_to_release(release, target) == 2
    result = plist.read_text(encoding="utf-8")
    assert "nexus-capability-actions-20261021-r22" in result
    assert "nexus-capability-actions-20261020-r20" not in result


def test_packaged_mcp_runtime_imports_only_from_release_tree(tmp_path: Path) -> None:
    release = tmp_path / "nexus-capability-actions-fixture-r99"
    package = release / "scripts/nexus_agent_platform"
    package.mkdir(parents=True)
    (package / "release_self_binding_probe.py").write_text(
        "RUNTIME_ROOT = __file__\n", encoding="utf-8"
    )

    probe = r"""
import pathlib, sys
root = pathlib.Path.cwd().resolve()
from nexus_agent_platform import release_self_binding_probe as loaded
assert pathlib.Path(loaded.__file__).resolve().is_relative_to(root), loaded.__file__
"""
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["PYTHONPATH"] = f"{release}:{release / 'scripts'}"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.run([sys.executable, "-c", probe], cwd=release, env=env, check=True)
