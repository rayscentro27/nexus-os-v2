import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import nexus_oracle_connection as oracle


class OracleConnectionAuthorityTests(unittest.TestCase):
    def connection(self, *, host="161.153.40.41", user="opc"):
        return {
            "host": host, "user": user, "identity_path": "~/.ssh/oracle_vm",
            "identity_public_fingerprint": "fingerprint", "remote_hostname": "nexus-llm-worker",
            "status": "VERIFIED",
        }

    def test_failed_current_does_not_try_history(self):
        record = {"current": self.connection(), "history": [
            {"host": "old-working-host", "user": "old-user", "identity_path": "old-key"}
        ]}
        calls = []

        def runner(args, **kwargs):
            calls.append(args)
            return subprocess.CompletedProcess(args, 255, "", "Permission denied (publickey)")

        with patch.object(oracle, "public_fingerprint", return_value="fingerprint"):
            with self.assertRaisesRegex(oracle.AuthorityError, "SSH_AUTHENTICATION_FAILED"):
                oracle.verify_connection(record["current"], runner=runner)
        self.assertEqual(len(calls), 1)
        self.assertIn("opc@161.153.40.41", calls[0])
        self.assertNotIn("old-working-host", str(calls))

    def test_failed_recovery_candidate_leaves_current_record_unchanged(self):
        original = {"current": self.connection(), "current_connection_count": 1, "history": []}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "authority.json"
            before = json.dumps(original, sort_keys=True)
            path.write_text(before)
            calls = []

            def runner(args, **kwargs):
                calls.append(args)
                return subprocess.CompletedProcess(args, 255, "", "Permission denied (publickey)")

            with patch.object(oracle, "public_fingerprint", return_value="candidate-fingerprint"):
                with self.assertRaises(oracle.AuthorityError):
                    oracle.promote_recovery_candidate(original, host="bad-host", user="opc",
                        identity_path="~/.ssh/oracle_vm", remote_hostname="bad-host",
                        runner=runner, path=path)
            self.assertEqual(path.read_text(), before)
            self.assertEqual(len(calls), 1)

    def test_safe_exec_rejects_shell_composition(self):
        with self.assertRaisesRegex(oracle.AuthorityError, "COMMAND_NOT_IN_READ_ONLY_ALLOWLIST"):
            oracle._safe_exec_args("hostname; cat ~/.ssh/oracle_vm")

    def test_safe_exec_allows_exact_research_provider_discovery_only(self):
        command = "podman exec nexus-hermes-0225 /opt/hermes/.venv/bin/hermes -p nova_nexus mcp test research"
        self.assertEqual(oracle._safe_exec_args(command), tuple(command.split()))
        with self.assertRaisesRegex(oracle.AuthorityError, "COMMAND_NOT_IN_READ_ONLY_ALLOWLIST"):
            oracle._safe_exec_args(command + " && id")

    def test_safe_exec_allows_only_native_hermes_configuration_help(self):
        command = "podman exec nexus-hermes-0225 /opt/hermes/.venv/bin/hermes config --help"
        self.assertEqual(oracle._safe_exec_args(command), tuple(command.split()))
        with self.assertRaisesRegex(oracle.AuthorityError, "COMMAND_NOT_IN_READ_ONLY_ALLOWLIST"):
            oracle._safe_exec_args(command.replace("--help", "set agent.max_turns 12"))

    def test_safe_exec_allows_only_read_of_active_hermes_turn_limit(self):
        command = ("podman exec nexus-hermes-0225 /opt/hermes/.venv/bin/hermes -p nova_nexus "
                   "config get agent.max_turns")
        self.assertEqual(oracle._safe_exec_args(command), tuple(command.split()))

    def test_acceptance_query_requires_bounded_selector(self):
        with self.assertRaisesRegex(oracle.AuthorityError, "ACCEPTANCE_QUERY_SELECTOR_REQUIRED"):
            oracle.validate_acceptance_query([], "", "", 10)
        with self.assertRaisesRegex(oracle.AuthorityError, "ACCEPTANCE_QUERY_SELECTOR_CONFLICT"):
            oracle.validate_acceptance_query(["123"], "2026-10-29T00:00:00Z", "2026-10-29T00:10:00Z", 10)
        with self.assertRaisesRegex(oracle.AuthorityError, "ACCEPTANCE_QUERY_MAX_RECORDS_INVALID"):
            oracle.validate_acceptance_query(["123"], "", "", 101)

    def test_acceptance_query_rejects_unbounded_or_malformed_inputs(self):
        with self.assertRaisesRegex(oracle.AuthorityError, "ACCEPTANCE_QUERY_UPDATE_ID_INVALID"):
            oracle.validate_acceptance_query(["../secret"], "", "", 10)
        with self.assertRaisesRegex(oracle.AuthorityError, "ACCEPTANCE_QUERY_WINDOW_INVALID"):
            oracle.validate_acceptance_query([], "2026-10-29T00:00:00Z", "", 10)

    def test_acceptance_session_query_is_exact_and_bounded(self):
        query = oracle.validate_acceptance_query([], "", "", 100, "acceptance_session_01")
        self.assertEqual(query, {"mode": "session", "session_id": "acceptance_session_01", "max_records": 100})
        with self.assertRaisesRegex(oracle.AuthorityError, "ACCEPTANCE_QUERY_SESSION_ID_INVALID"):
            oracle.validate_acceptance_query([], "", "", 10, "../outside")
        with self.assertRaisesRegex(oracle.AuthorityError, "ACCEPTANCE_QUERY_SELECTOR_CONFLICT"):
            oracle.validate_acceptance_query(["123"], "", "", 10, "acceptance_session_01")

    def test_acceptance_exact_message_query_is_bounded_to_time_window(self):
        query = oracle.validate_acceptance_query(
            [], "2026-11-02T00:00:00Z", "2026-11-03T00:00:00Z", 10,
            messages=["What is Systems doing right now?", "What did Research find?"])
        self.assertEqual(query["mode"], "messages")
        self.assertEqual(len(query["messages"]), 2)
        with self.assertRaisesRegex(oracle.AuthorityError, "ACCEPTANCE_QUERY_WINDOW_REQUIRED"):
            oracle.validate_acceptance_query([], "", "", 10, messages=["test"])
        with self.assertRaisesRegex(oracle.AuthorityError, "ACCEPTANCE_QUERY_MESSAGE_INVALID"):
            oracle.validate_acceptance_query([], "2026-11-02T00:00:00Z", "2026-11-03T00:00:00Z", 10,
                                             messages=["x" * 501])

    def test_acceptance_script_uses_fixed_roots_and_read_only_database_mode(self):
        script = oracle.NOVA_ACCEPTANCE_EVIDENCE_SCRIPT
        self.assertIn("repo=Path('/home/opc/nexus-os-v2-source')", script)
        self.assertIn("contexts=runtime/'nova_context_snapshots'", script)
        self.assertIn("/home/opc/.nexus/state/nova/agent_traces", script)
        self.assertNotIn("sqlite3.connect(", script)
        self.assertNotIn("open(.*,'w'", script)
        self.assertIn("'read_only':True", script)


if __name__ == "__main__":
    unittest.main()
