from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from checks.provider_surface_guard import check, discover_provider_files, unregistered_provider_files


def test_provider_surface_guard_accepts_only_registered_runtime_surfaces():
    result = check()
    assert result["ok"] is True
    assert result["locked_source_drift"] == []
    assert result["unscoped_bypass"] == []
    assert result["partial"] == []
    assert result["unknown"] == []
    assert result["missing_secret_mappings"] == []
    assert result["unregistered_provider_files"] == []


def test_new_provider_call_forms_fail_discovery(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    samples = {
        "requests_case.py": "import requests\nrequests.post('https://api.openrouter.ai/v1/chat')\n",
        "fetch_case.mjs": "fetch('https://api.example.invalid/v1/action')\n",
        "sdk_case.py": "from openai import OpenAI\nclient = OpenAI()\n",
    }
    for name, source in samples.items():
        (scripts / name).write_text(source)
    discovered = discover_provider_files(tmp_path)
    assert discovered == {f"scripts/{name}" for name in samples}
    assert unregistered_provider_files(tmp_path, set()) == sorted(discovered)


def test_approved_boundary_and_non_runtime_references_are_ignored(tmp_path):
    wrapper = tmp_path / "scripts/nexus_agent_platform/provider_enforcement.py"
    wrapper.parent.mkdir(parents=True)
    wrapper.write_text("import requests\nrequests.post('https://api.openrouter.ai/v1/chat')\n")
    fixture = tmp_path / "scripts/tests/test_provider_mock.py"
    fixture.parent.mkdir(parents=True)
    fixture.write_text("import requests\nrequests.post('https://api.openrouter.ai/v1/chat')\n")
    docs = tmp_path / "scripts/reference.py"
    docs.write_text("MESSAGE = \"requests.post('https://api.openrouter.ai/v1/chat')\"\n")
    assert discover_provider_files(tmp_path) == set()


def test_unregistered_direct_provider_file_is_a_guard_failure(tmp_path):
    source = tmp_path / "scripts/new_provider.py"
    source.parent.mkdir(parents=True)
    source.write_text("import requests\nrequests.post('https://api.example.invalid/action')\n")
    assert unregistered_provider_files(tmp_path, set()) == ["scripts/new_provider.py"]
