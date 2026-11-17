from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from services.nexus_mcp import server
from services.nexus_mcp.server import _action_call


class ResearchIntakeEgressScopeTests(unittest.TestCase):
    def test_research_intake_replaces_stale_feeder_scope_and_restores_environment(self):
        os.environ["NEXUS_DURABLE_JOB_ID"] = "feeder-process-27046"
        os.environ.pop("NEXUS_DURABLE_EXECUTION_ID", None)
        seen = {}

        def operation(**_arguments):
            seen["job_id"] = os.environ.get("NEXUS_DURABLE_JOB_ID")
            seen["execution_id"] = os.environ.get("NEXUS_DURABLE_EXECUTION_ID")
            return {"status": "queued"}

        with patch("services.nexus_mcp.server.authorize_action"):
            result = _action_call("nexus_assign_research", operation, {})

        self.assertEqual(result["status"], "queued")
        self.assertEqual(seen["job_id"], result["request_id"])
        self.assertEqual(seen["execution_id"], result["request_id"])
        self.assertEqual(os.environ["NEXUS_DURABLE_JOB_ID"], "feeder-process-27046")
        self.assertNotIn("NEXUS_DURABLE_EXECUTION_ID", os.environ)

    def test_other_mcp_actions_do_not_change_egress_scope(self):
        os.environ["NEXUS_DURABLE_JOB_ID"] = "worker-job-123"
        seen = {}

        def operation(**_arguments):
            seen["job_id"] = os.environ.get("NEXUS_DURABLE_JOB_ID")
            return {"status": "ok"}

        with patch("services.nexus_mcp.server.authorize_action"):
            _action_call("nexus_get_research_case", operation, {})
        self.assertEqual(seen["job_id"], "worker-job-123")

    def test_research_controller_read_uses_local_mirror_and_does_not_consume_external_egress(self):
        os.environ["NEXUS_DURABLE_JOB_ID"] = "feeder-process-17305"
        observed = {}

        def exact(*args):
            observed["local_only"] = os.environ.get("NEXUS_RESEARCH_CASE_READ_LOCAL_ONLY")
            return ({"case_id": args[0]}, {}, None)

        class Controller:
            @staticmethod
            def _local_case_read_scope():
                from nexus_agent_platform.research_room.production_controller import _local_case_read_scope
                return _local_case_read_scope()
            @staticmethod
            def status(*args):
                observed["job_id"] = os.environ.get("NEXUS_DURABLE_JOB_ID")
                observed["local_status_read"] = True
                return {"status": "ok", "read_source": "LOCAL_DURABLE_MIRROR"}

        with patch.object(server, "_exact_research_case", exact), \
             patch("nexus_agent_platform.research_room.production_controller.status", Controller.status):
            result = server._research_controller_read("status", "case", "objective", "project", "job")

        self.assertEqual(result["read_source"], "LOCAL_DURABLE_MIRROR")
        self.assertEqual(observed["local_only"], "1")
        self.assertEqual(observed["job_id"], "feeder-process-17305")
        self.assertNotIn("NEXUS_RESEARCH_CASE_READ_LOCAL_ONLY", os.environ)

    def test_controller_mutation_scopes_but_does_not_expand_egress_budget(self):
        os.environ["NEXUS_DURABLE_JOB_ID"] = "feeder-process-17305"
        seen = {}

        def operation(**_arguments):
            seen["job_id"] = os.environ.get("NEXUS_DURABLE_JOB_ID")
            seen["execution_id"] = os.environ.get("NEXUS_DURABLE_EXECUTION_ID")
            seen["budget"] = __import__("json").loads(os.environ["NEXUS_JOB_BUDGET"])
            return {"status": "advanced"}

        with patch("services.nexus_mcp.server.authorize_action"):
            result = _action_call("nexus_research_controller_continue", operation, {})
        self.assertEqual(seen["job_id"], result["request_id"])
        self.assertEqual(seen["execution_id"], result["request_id"])
        self.assertEqual(seen["budget"]["max_requests"], 32)
        self.assertEqual(os.environ["NEXUS_DURABLE_JOB_ID"], "feeder-process-17305")
