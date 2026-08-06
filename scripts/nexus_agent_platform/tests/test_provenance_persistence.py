"""Cross-process tests for Hermes provenance persistence.

These tests verify that operational provenance survives separate --once
worker process exits. Each test uses subprocess to simulate separate
Python processes, proving that the persistent context store works across
process boundaries.

Tests confined to a single Python process are NOT sufficient.
"""

import json
import os
import subprocess
import sys
import tempfile
import time

import pytest


_REPO = os.path.join(os.path.dirname(__file__), "..", "..", "..")
_SCRIPTS = os.path.join(_REPO, "scripts")
_PYTHON = os.path.join(_REPO, ".venv-agent-platform", "bin", "python3")
_STORE_DIR = os.path.expanduser("~/.config/nexus/hermes_context")


def _run_process(code: str, env: dict = None) -> subprocess.CompletedProcess:
    """Run a Python code snippet in a subprocess."""
    full_env = os.environ.copy()
    full_env["PYTHONPATH"] = _SCRIPTS
    if env:
        full_env.update(env)
    return subprocess.run(
        [_PYTHON, "-c", code],
        capture_output=True, text=True, timeout=30,
        env=full_env,
        cwd=_REPO,
    )


class TestCrossProcessProvenancePersistence:
    """Provenance must survive separate process executions."""

    def test_process_a_saves_process_b_reads(self):
        """Process A saves capability result, Process B reads it."""
        chat_id = 999000001  # test chat ID

        # Process A: save a capability result
        code_a = f"""
import sys
sys.path.insert(0, "{_SCRIPTS}")
from nexus_agent_platform.context.hermes_store import save_capability_result, load_conversation

save_capability_result({chat_id}, "get_client_count", {{
    "status": "ok",
    "data": {{
        "production_total": 14,
        "active": 14,
        "onboarding": 0,
        "tester_or_certification": 24,
    }},
    "provenance": {{
        "capability": "get_client_count",
        "status": "success",
        "source": "supabase",
        "source_type": "live_governed_read",
        "retrieved_at": "2026-08-06T22:00:00Z",
        "freshness": "live",
        "query_target": "https://test.supabase.co/rest/v1/client_profiles",
        "filters": {{"select": "tenant_id,status"}},
        "trace_id": "trace_process_a",
    }},
}})

ctx = load_conversation({chat_id})
print("SAVED")
print(f"capability={{ctx.get('last_capability')}}")
print(f"source={{ctx.get('last_capability_result', {{}}).get('source')}}")
print(f"freshness={{ctx.get('last_capability_result', {{}}).get('freshness')}}")
"""
        result_a = _run_process(code_a)
        assert result_a.returncode == 0, f"Process A failed: {result_a.stderr}"
        assert "SAVED" in result_a.stdout

        # Process B: read the capability result (simulates next --once cycle)
        code_b = f"""
import sys
sys.path.insert(0, "{_SCRIPTS}")
from nexus_agent_platform.context.hermes_store import load_conversation, get_last_capability_result

ctx = load_conversation({chat_id})
print("LOADED")
print(f"capability={{ctx.get('last_capability')}}")

result = get_last_capability_result({chat_id})
print(f"source={{result.get('source') if result else 'NONE'}}")
print(f"freshness={{result.get('freshness') if result else 'NONE'}}")
print(f"trace_id={{result.get('trace_id') if result else 'NONE'}}")
"""
        result_b = _run_process(code_b)
        assert result_b.returncode == 0, f"Process B failed: {result_b.stderr}"
        assert "LOADED" in result_b.stdout
        assert "source=supabase" in result_b.stdout
        assert "freshness=live" in result_b.stdout
        assert "trace_id=trace_process_a" in result_b.stdout

        # Cleanup
        from nexus_agent_platform.context.hermes_store import clear_conversation
        clear_conversation(chat_id)

    def test_process_c_provenance_followup(self):
        """Process C asks provenance question, gets answer from persisted context."""
        chat_id = 999000002

        # Process A: save capability result
        code_save = f"""
import sys
sys.path.insert(0, "{_SCRIPTS}")
from nexus_agent_platform.context.hermes_store import save_capability_result

save_capability_result({chat_id}, "get_client_count", {{
    "status": "ok",
    "data": {{"production_total": 14, "active": 14}},
    "provenance": {{
        "capability": "get_client_count",
        "status": "success",
        "source": "supabase",
        "source_type": "live_governed_read",
        "retrieved_at": "2026-08-06T22:00:00Z",
        "freshness": "live",
        "query_target": "https://test.supabase.co/rest/v1/client_profiles",
        "filters": {{}},
        "trace_id": "trace_process_c",
    }},
}})
print("SAVED")
"""
        result_save = _run_process(code_save)
        assert result_save.returncode == 0

        # Process B: detect provenance follow-up and generate response
        code_followup = f"""
import sys
sys.path.insert(0, "{_SCRIPTS}")
from nexus_agent_platform.agents.front_brain import detect_provenance_followup, generate_provenance_response
from nexus_agent_platform.context.hermes_store import get_last_capability_result

# Test detection
assert detect_provenance_followup("Where did you get that information?")
assert detect_provenance_followup("Did that come from Supabase?")
assert detect_provenance_followup("Is that live data?")
assert detect_provenance_followup("When was it retrieved?")
assert detect_provenance_followup("How current is that?")
assert detect_provenance_followup("Which capability did you use?")
assert detect_provenance_followup("Are you sure about that number?")
assert not detect_provenance_followup("How many clients do we have?")
assert not detect_provenance_followup("Hello Hermes")

# Test response generation from persisted context
result = get_last_capability_result({chat_id})
response = generate_provenance_response("Where did you get that information from?", result)
assert response is not None
assert "supabase" in response.lower()
assert "get client count" in response.lower()
assert "governed" in response.lower()
print("PROVENANCE_OK")
print(f"response_preview={{response[:100]}}")
"""
        result_followup = _run_process(code_followup)
        assert result_followup.returncode == 0, f"Process B failed: {result_followup.stderr}"
        assert "PROVENANCE_OK" in result_followup.stdout

        # Cleanup
        from nexus_agent_platform.context.hermes_store import clear_conversation
        clear_conversation(chat_id)

    def test_expired_context_returns_empty(self):
        """Expired context must not return stale data."""
        chat_id = 999000003

        # Process A: save with very short TTL
        code_save = f"""
import sys, time
sys.path.insert(0, "{_SCRIPTS}")
from nexus_agent_platform.context.hermes_store import save_conversation, load_conversation

ctx = {{
    "last_capability": "get_client_count",
    "last_capability_result": {{
        "capability": "get_client_count",
        "status": "success",
        "source": "supabase",
        "freshness": "live",
        "retrieved_at": "2026-08-06T22:00:00Z",
    }},
    "expires_at": time.time() + 1,  # expires in 1 second
}}
save_conversation({chat_id}, ctx)
print("SAVED")
"""
        result_save = _run_process(code_save)
        assert result_save.returncode == 0

        # Process B: wait 2 seconds then read (should be expired)
        code_expired = f"""
import sys, time
sys.path.insert(0, "{_SCRIPTS}")
from nexus_agent_platform.context.hermes_store import load_conversation, get_last_capability_result

time.sleep(2)
ctx = load_conversation({chat_id})
result = get_last_capability_result({chat_id})
print(f"ctx_empty={{not ctx}}")
print(f"result_none={{result is None}}")
"""
        result_expired = _run_process(code_expired)
        assert result_expired.returncode == 0
        assert "ctx_empty=True" in result_expired.stdout
        assert "result_none=True" in result_expired.stdout

    def test_corrupted_context_returns_empty(self):
        """Corrupted JSON file must not crash — returns empty dict."""
        chat_id = 999000004
        from nexus_agent_platform.context.hermes_store import _store_path
        path = _store_path(chat_id)

        # Write corrupted JSON
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write("{invalid json {{{")

        # Process A: try to read corrupted file
        code = f"""
import sys
sys.path.insert(0, "{_SCRIPTS}")
from nexus_agent_platform.context.hermes_store import load_conversation, get_last_capability_result

ctx = load_conversation({chat_id})
result = get_last_capability_result({chat_id})
print(f"ctx_empty={{not ctx}}")
print(f"result_none={{result is None}}")
"""
        result = _run_process(code)
        assert result.returncode == 0
        assert "ctx_empty=True" in result.stdout
        assert "result_none=True" in result.stdout

        # Cleanup
        if os.path.exists(path):
            os.unlink(path)

    def test_another_chat_isolation(self):
        """Different chat IDs must be completely isolated."""
        chat_a = 999000005
        chat_b = 999000006

        # Process A: save to chat A
        code_a = f"""
import sys
sys.path.insert(0, "{_SCRIPTS}")
from nexus_agent_platform.context.hermes_store import save_capability_result

save_capability_result({chat_a}, "get_client_count", {{
    "status": "ok",
    "data": {{"production_total": 14}},
    "provenance": {{"source": "supabase", "freshness": "live", "trace_id": "trace_a"}},
}})
print("SAVED_A")
"""
        result_a = _run_process(code_a)
        assert result_a.returncode == 0

        # Process B: read chat B (should be empty)
        code_b = f"""
import sys
sys.path.insert(0, "{_SCRIPTS}")
from nexus_agent_platform.context.hermes_store import get_last_capability_result

result = get_last_capability_result({chat_b})
print(f"chat_b_result={{result}}")
"""
        result_b = _run_process(code_b)
        assert result_b.returncode == 0
        assert "chat_b_result=None" in result_b.stdout

        # Cleanup
        from nexus_agent_platform.context.hermes_store import clear_conversation
        clear_conversation(chat_a)
        clear_conversation(chat_b)

    def test_failed_query_does_not_return_stale_count(self):
        """A failed query must not return a stale count as current."""
        chat_id = 999000007

        # Process A: save a FAILED result
        code_save = f"""
import sys
sys.path.insert(0, "{_SCRIPTS}")
from nexus_agent_platform.context.hermes_store import save_capability_result

save_capability_result({chat_id}, "get_client_count", {{
    "status": "unavailable",
    "data": {{"production_total": 0}},
    "provenance": {{
        "capability": "get_client_count",
        "status": "error",
        "source": "supabase",
        "freshness": "unknown",
        "trace_id": "trace_failed",
    }},
}})
print("SAVED_FAILED")
"""
        result_save = _run_process(code_save)
        assert result_save.returncode == 0

        # Process B: provenance follow-up must not claim success
        code_check = f"""
import sys
sys.path.insert(0, "{_SCRIPTS}")
from nexus_agent_platform.agents.front_brain import generate_provenance_response
from nexus_agent_platform.context.hermes_store import get_last_capability_result

result = get_last_capability_result({chat_id})
response = generate_provenance_response("Where did you get that?", result)
assert response is not None
assert "did not complete successfully" in response.lower() or "error" in response.lower()
print("STALE_BLOCKED")
"""
        result_check = _run_process(code_check)
        assert result_check.returncode == 0
        assert "STALE_BLOCKED" in result_check.stdout

        # Cleanup
        from nexus_agent_platform.context.hermes_store import clear_conversation
        clear_conversation(chat_id)

    def test_safe_permissions(self):
        """Context store files must have 0600 permissions."""
        chat_id = 999000008
        from nexus_agent_platform.context.hermes_store import _store_path, save_conversation

        save_conversation(chat_id, {"last_mode": "test"})
        path = _store_path(chat_id)

        mode = os.stat(path).st_mode
        # Check owner-only read/write (0600)
        assert mode & 0o7777 == 0o600, f"Expected 0600, got {oct(mode & 0o7777)}"

        # Cleanup
        from nexus_agent_platform.context.hermes_store import clear_conversation
        clear_conversation(chat_id)

    def test_concurrent_file_writes(self):
        """Multiple rapid writes must not corrupt the file."""
        chat_id = 999000009
        from nexus_agent_platform.context.hermes_store import save_conversation, load_conversation

        # Write many times rapidly
        for i in range(20):
            save_conversation(chat_id, {"counter": i, "last_mode": f"mode_{i}"})

        # Verify final state is valid JSON
        ctx = load_conversation(chat_id)
        assert isinstance(ctx, dict)
        assert ctx.get("counter") == 19
        assert ctx.get("last_mode") == "mode_19"

        # Cleanup
        from nexus_agent_platform.context.hermes_store import clear_conversation
        clear_conversation(chat_id)

    def test_reset_clears_context(self):
        """clear_conversation must remove the file."""
        chat_id = 999000010
        from nexus_agent_platform.context.hermes_store import (
            save_conversation, load_conversation, clear_conversation, _store_path,
        )

        save_conversation(chat_id, {"last_mode": "test"})
        assert load_conversation(chat_id) != {}

        clear_conversation(chat_id)
        assert load_conversation(chat_id) == {}
        assert not os.path.exists(_store_path(chat_id))

    def test_unsafe_fields_rejected(self):
        """Unsafe fields must be stripped from persisted context."""
        chat_id = 999000011
        from nexus_agent_platform.context.hermes_store import (
            save_capability_result, load_conversation, clear_conversation,
        )

        save_capability_result(chat_id, "get_client_count", {
            "status": "ok",
            "data": {
                "production_total": 14,
                "active": 14,
                "client_name": "SECRET NAME",
                "client_email": "secret@example.com",
            },
            "provenance": {
                "status": "success",
                "source": "supabase",
                "source_type": "live_governed_read",
                "retrieved_at": "2026-08-06T22:00:00Z",
                "freshness": "live",
                "token": "SECRET_TOKEN",
                "service_role_key": "SECRET_KEY",
                "bot_token": "SECRET_BOT",
                "api_key": "SECRET_API",
                "secret": "SECRET",
                "password": "SECRET_PW",
                "trace_id": "trace_test",
            },
        })

        ctx = load_conversation(chat_id)
        pcr = ctx.get("last_capability_result", {})

        # Verify unsafe fields are NOT present
        assert "token" not in pcr
        assert "service_role_key" not in pcr
        assert "bot_token" not in pcr
        assert "api_key" not in pcr
        assert "secret" not in pcr
        assert "password" not in pcr
        assert "client_name" not in pcr.get("safe_summary", {})
        assert "client_email" not in pcr.get("safe_summary", {})

        # Verify safe fields ARE present
        assert pcr.get("capability") == "get_client_count"
        assert pcr.get("source") == "supabase"
        assert pcr.get("freshness") == "live"
        assert pcr.get("safe_summary", {}).get("production_clients") == 14
        assert pcr.get("safe_summary", {}).get("active") == 14

        clear_conversation(chat_id)

    def test_schema_version_in_context(self):
        """Persisted context must include schema_version."""
        chat_id = 999000012
        from nexus_agent_platform.context.hermes_store import (
            save_conversation, load_conversation, clear_conversation, _SCHEMA_VERSION,
        )

        save_conversation(chat_id, {"last_mode": "test"})
        ctx = load_conversation(chat_id)
        assert ctx.get("schema_version") == _SCHEMA_VERSION

        clear_conversation(chat_id)

    def test_old_schema_rejected(self):
        """Context with older schema version must be rejected."""
        chat_id = 999000013
        from nexus_agent_platform.context.hermes_store import (
            save_conversation, load_conversation, clear_conversation, _store_path,
        )

        # Manually write old schema
        path = _store_path(chat_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump({"last_mode": "test", "schema_version": 0}, f)

        ctx = load_conversation(chat_id)
        assert ctx == {}  # rejected

        clear_conversation(chat_id)

    def test_no_raw_telegram_id_in_filename(self):
        """Filenames must be hashed, not raw Telegram IDs."""
        chat_id = 123456789
        from nexus_agent_platform.context.hermes_store import _store_path
        path = _store_path(chat_id)
        filename = os.path.basename(path)
        assert "123456789" not in filename
        assert filename.endswith(".json")
        # Must be a hex hash
        assert len(filename.replace(".json", "")) == 16
        int(filename.replace(".json", ""), 16)  # must not raise

    def test_no_secrets_in_context_files(self):
        """Generated context files must not contain secret-like patterns."""
        chat_id = 999000014
        from nexus_agent_platform.context.hermes_store import (
            save_capability_result, clear_conversation, _store_path,
        )

        save_capability_result(chat_id, "get_client_count", {
            "status": "ok",
            "data": {"production_total": 14, "active": 14},
            "provenance": {
                "status": "success",
                "source": "supabase",
                "source_type": "live_governed_read",
                "retrieved_at": "2026-08-06T22:00:00Z",
                "freshness": "live",
                "query_target": "https://test.supabase.co/rest/v1/client_profiles",
                "filters": {},
                "trace_id": "trace_test",
            },
        })

        path = _store_path(chat_id)
        with open(path) as f:
            content = f.read()

        # Check for common secret patterns
        secret_patterns = [
            "service_role", "SUPABASE_SERVICE", "bot_token", "TELEGRAM_BOT",
            "api_key", "API_KEY", "sk-", "eyJ", "password", "SECRET",
            "credentials", "authorization",
        ]
        for pattern in secret_patterns:
            assert pattern.lower() not in content.lower(), (
                f"Found secret pattern '{pattern}' in context file"
            )

        clear_conversation(chat_id)


class TestProvenanceResponseWording:
    """Provenance responses must correctly distinguish source from access boundary."""

    LIVE_RESULT = {
        "capability": "get_client_count",
        "result_id": "trace_live",
        "status": "ok",
        "source": "supabase",
        "source_type": "live_governed_read",
        "retrieved_at": "2026-08-06T22:00:00Z",
        "freshness": "live",
        "query_target": "https://test.supabase.co/rest/v1/client_profiles",
        "filters": {},
        "access_boundary": "certified capability only",
        "trace_id": "trace_live",
        "safe_summary": {
            "production_clients": 14,
            "active": 14,
            "onboarding": 0,
            "tester_or_certification": 24,
        },
    }

    CACHED_RESULT = {
        "capability": "get_client_count",
        "result_id": "trace_cached",
        "status": "ok",
        "source": "supabase",
        "source_type": "cached_governed_read",
        "retrieved_at": "2026-08-06T21:00:00Z",
        "freshness": "cached",
        "query_target": "https://test.supabase.co/rest/v1/client_profiles",
        "filters": {},
        "access_boundary": "certified capability only",
        "trace_id": "trace_cached",
        "safe_summary": {"production_clients": 14, "active": 14},
    }

    TEST_RESULT = {
        "capability": "get_client_count",
        "result_id": "trace_test",
        "status": "ok",
        "source": "test_data",
        "source_type": "test_data",
        "retrieved_at": "2026-08-06T20:00:00Z",
        "freshness": "unknown",
        "query_target": "",
        "filters": {},
        "access_boundary": "certified capability only",
        "trace_id": "trace_test",
        "safe_summary": {},
    }

    LOCAL_RESULT = {
        "capability": "get_system_status",
        "result_id": "trace_local",
        "status": "ok",
        "source": "local_file",
        "source_type": "local_runtime_read",
        "retrieved_at": "2026-08-06T22:00:00Z",
        "freshness": "live",
        "query_target": "nexus_process_registry.json",
        "filters": {},
        "access_boundary": "certified capability only",
        "trace_id": "trace_local",
        "safe_summary": {},
    }

    def test_live_supabase_directly_answered_yes(self):
        """'Did that come directly from Supabase?' must answer yes for live governed read."""
        from nexus_agent_platform.agents.front_brain import generate_provenance_response
        resp = generate_provenance_response(
            "So you did get that directly from Supabase?", self.LIVE_RESULT
        )
        assert resp is not None
        assert resp.lower().startswith("yes")
        assert "supabase" in resp.lower()
        assert "governed capability" in resp.lower()
        assert "unrestricted" not in resp.lower() or "not unrestricted" in resp.lower()

    def test_live_supabase_so_you_queried(self):
        """'So you queried Supabase?' must answer yes for live governed read."""
        from nexus_agent_platform.agents.front_brain import generate_provenance_response
        resp = generate_provenance_response(
            "So you queried Supabase?", self.LIVE_RESULT
        )
        assert resp is not None
        assert resp.lower().startswith("yes")

    def test_cached_supabase_not_direct(self):
        """Cached result must not claim direct live query."""
        from nexus_agent_platform.agents.front_brain import generate_provenance_response
        resp = generate_provenance_response(
            "Is that cached data?", self.CACHED_RESULT
        )
        assert resp is not None
        # Should identify it as cached
        assert "cached" in resp.lower()

    def test_test_data_not_supabase(self):
        """Test data must not claim Supabase source."""
        from nexus_agent_platform.agents.front_brain import generate_provenance_response
        resp = generate_provenance_response(
            "Did that come from Supabase?", self.TEST_RESULT
        )
        assert resp is not None
        assert "no" in resp.lower() or "test" in resp.lower()

    def test_local_runtime_not_supabase(self):
        """Local runtime read must not claim Supabase source."""
        from nexus_agent_platform.agents.front_brain import generate_provenance_response
        resp = generate_provenance_response(
            "Did that come from Supabase?", self.LOCAL_RESULT
        )
        assert resp is not None
        assert "no" in resp.lower() or "local" in resp.lower()

    def test_concise_capability_answer(self):
        """'Which capability did you use?' must be concise."""
        from nexus_agent_platform.agents.front_brain import generate_provenance_response
        resp = generate_provenance_response(
            "Which capability did you use?", self.LIVE_RESULT
        )
        assert resp is not None
        assert "get client count" in resp.lower()
        # Must be concise — just the capability name
        assert len(resp) < 50

    def test_phoenix_time_displayed(self):
        """'When was it retrieved?' must show Phoenix-local time."""
        from nexus_agent_platform.agents.front_brain import generate_provenance_response
        resp = generate_provenance_response(
            "When was it retrieved?", self.LIVE_RESULT
        )
        assert resp is not None
        assert "phoenix" in resp.lower()

    def test_no_unrestricted_database_claim(self):
        """Provenance must never claim unrestricted database access."""
        from nexus_agent_platform.agents.front_brain import generate_provenance_response
        questions = [
            "Where did you get that?",
            "So you did get that directly from Supabase?",
            "Is that live data?",
            "When was it retrieved?",
            "Which capability did you use?",
            "Was that cached?",
        ]
        for q in questions:
            resp = generate_provenance_response(q, self.LIVE_RESULT)
            if resp:
                # Should not claim unrestricted access without negation
                assert "unrestricted database access" not in resp.lower() or \
                    "not unrestricted" in resp.lower() or \
                    "do not have unrestricted" in resp.lower(), \
                    f"Question '{q}' produced unrestricted access claim"

    def test_live_result_source_not_denied(self):
        """Live Supabase result must not deny its Supabase source."""
        from nexus_agent_platform.agents.front_brain import generate_provenance_response
        resp = generate_provenance_response(
            "So you did get that directly from Supabase?", self.LIVE_RESULT
        )
        assert resp is not None
        # Must NOT say "no" when it was a live Supabase query
        first_word = resp.strip().split()[0].lower().rstrip(".")
        assert first_word == "yes", f"Expected 'yes', got '{first_word}' in: {resp}"

    def test_no_response_without_result(self):
        """No provenance result must return None."""
        from nexus_agent_platform.agents.front_brain import generate_provenance_response
        assert generate_provenance_response("Where did you get that?", None) is None
        assert generate_provenance_response("Where did you get that?", {}) is None
