import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from nexus_agent_platform.bridge.oracle_hermes_cli import _remote_command  # noqa: E402


def test_oracle_bridge_uses_native_create_or_resume_sessions():
    command = _remote_command()
    assert "chat -Q --query-file -" in command
    assert "--continue \"$session\"" in command
    assert "--create-if-missing" in command
    assert "--resume \"$session\"" not in command
    assert "--pass-session-id" in command


def test_oracle_bridge_keeps_profile_and_toolset_canonical():
    command = _remote_command()
    assert "HERMES_HOME=/opt/data/profiles/nova_nexus" in command
    assert "HERMES_PROFILE=nova_nexus" in command
    assert "-t nexus_mcp_remote" in command
