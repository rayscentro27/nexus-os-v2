"""Tests for Hermes Nova — isolated conversational Telegram agent.

Tests cover:
1. SOUL definition
2. Response mode classification
3. Simple utilities (time, arithmetic)
4. Conversation memory (load, save, reset, isolation)
5. Response validation
6. Graph structure and node registration
7. Model configuration
8. Feature flag
9. No side effects on import
"""

import os
import sys
import time
from unittest import mock

import pytest

_scripts_dir = os.path.join(os.path.dirname(__file__), "..")
if _scripts_dir not in sys.path:
    sys.path.insert(0, _scripts_dir)


class TestNovaSoul:
    """Verify Nova has an isolated, conversational SOUL."""

    def test_soul_exists(self):
        from nexus_agent_platform.agents.nova import SOUL
        assert SOUL
        assert len(SOUL) > 100

    def test_soul_is_conversational(self):
        from nexus_agent_platform.agents.nova import SOUL
        soul_lower = SOUL.lower()
        assert "conversational" in soul_lower or "natural" in soul_lower

    def test_soul_mentions_ai_honesty(self):
        from nexus_agent_platform.agents.nova import SOUL
        soul_lower = SOUL.lower()
        assert "honest" in soul_lower or "ai" in soul_lower

    def test_soul_not_command_menu(self):
        from nexus_agent_platform.agents.nova import SOUL
        soul_lower = SOUL.lower()
        assert "command menu" not in soul_lower
        assert "/status" not in SOUL

    def test_soul_not_system_status_bot(self):
        from nexus_agent_platform.agents.nova import SOUL
        soul_lower = SOUL.lower()
        assert "system status bot" not in soul_lower

    def test_soul_not_research_only(self):
        from nexus_agent_platform.agents.nova import SOUL
        soul_lower = SOUL.lower()
        assert "research only" not in soul_lower or "not research-only" in soul_lower

    def test_soul_allows_disagreement(self):
        from nexus_agent_platform.agents.nova import SOUL
        soul_lower = SOUL.lower()
        assert "disagree" in soul_lower


class TestResponseModeClassification:
    """Verify mode classification covers all required patterns."""

    def test_greeting(self):
        from nexus_agent_platform.agents.nova import classify_response_mode
        assert classify_response_mode("hello") == "GREETING"
        assert classify_response_mode("good morning") == "GREETING"
        assert classify_response_mode("hey") == "GREETING"

    def test_how_are_you(self):
        from nexus_agent_platform.agents.nova import classify_response_mode
        assert classify_response_mode("how are you today?") == "HOW_ARE_YOU"
        assert classify_response_mode("how's it going?") == "HOW_ARE_YOU"

    def test_time_request(self):
        from nexus_agent_platform.agents.nova import classify_response_mode
        assert classify_response_mode("what time is it?") == "TIME_REQUEST"
        assert classify_response_mode("what day is it?") == "TIME_REQUEST"

    def test_arithmetic(self):
        from nexus_agent_platform.agents.nova import classify_response_mode
        assert classify_response_mode("2 + 3") == "ARITHMETIC"
        assert classify_response_mode("what is 10 * 5") == "ARITHMETIC"

    def test_conversation_reset(self):
        from nexus_agent_platform.agents.nova import classify_response_mode
        assert classify_response_mode("reset conversation") == "CONVERSATION_RESET"
        assert classify_response_mode("start over") == "CONVERSATION_RESET"

    def test_opinion(self):
        from nexus_agent_platform.agents.nova import classify_response_mode
        assert classify_response_mode("what do you think about AI?") == "OPINION"

    def test_general_conversation(self):
        from nexus_agent_platform.agents.nova import classify_response_mode
        assert classify_response_mode("tell me about LangGraph") == "CONVERSATION"
        assert classify_response_mode("I am thinking about launching a product") == "CONVERSATION"


class TestSimpleUtilities:
    """Verify simple utilities that don't need the model."""

    def test_phoenix_time_format(self):
        from nexus_agent_platform.agents.nova import _get_phoenix_time
        result = _get_phoenix_time()
        assert "Phoenix" in result
        assert "AM" in result or "PM" in result

    def test_phoenix_date_format(self):
        from nexus_agent_platform.agents.nova import _get_phoenix_date
        result = _get_phoenix_date()
        assert "Today is" in result
        assert "2026" in result or "2025" in result

    def test_arithmetic_addition(self):
        from nexus_agent_platform.agents.nova import _evaluate_arithmetic
        assert _evaluate_arithmetic("123 + 456") == "579"

    def test_arithmetic_subtraction(self):
        from nexus_agent_platform.agents.nova import _evaluate_arithmetic
        assert _evaluate_arithmetic("10 - 3") == "7"

    def test_arithmetic_multiplication(self):
        from nexus_agent_platform.agents.nova import _evaluate_arithmetic
        assert _evaluate_arithmetic("6 * 7") == "42"

    def test_arithmetic_division(self):
        from nexus_agent_platform.agents.nova import _evaluate_arithmetic
        assert _evaluate_arithmetic("10 / 4") == "2.5"

    def test_arithmetic_modulo(self):
        from nexus_agent_platform.agents.nova import _evaluate_arithmetic
        assert _evaluate_arithmetic("10 % 3") == "1"

    def test_arithmetic_by_zero(self):
        from nexus_agent_platform.agents.nova import _evaluate_arithmetic
        assert _evaluate_arithmetic("10 / 0") == "I can't divide by zero."

    def test_arithmetic_no_match(self):
        from nexus_agent_platform.agents.nova import _evaluate_arithmetic
        assert _evaluate_arithmetic("hello world") is None


class TestConversationMemory:
    """Verify isolated conversation memory system."""

    def test_save_and_load(self, tmp_path):
        from nexus_agent_platform.agents import nova
        original_dir = nova.MEMORY_DIR
        nova.MEMORY_DIR = str(tmp_path)
        try:
            messages = [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi there"},
            ]
            nova.save_memory(99999, messages)
            loaded = nova.load_memory(99999)
            assert len(loaded) == 2
            assert loaded[0]["role"] == "user"
            assert loaded[0]["content"] == "hello"
        finally:
            nova.MEMORY_DIR = original_dir

    def test_reset_memory(self, tmp_path):
        from nexus_agent_platform.agents import nova
        original_dir = nova.MEMORY_DIR
        nova.MEMORY_DIR = str(tmp_path)
        try:
            nova.save_memory(99998, [{"role": "user", "content": "test"}])
            nova.reset_memory(99998)
            loaded = nova.load_memory(99998)
            assert len(loaded) == 0
        finally:
            nova.MEMORY_DIR = original_dir

    def test_isolation_between_chats(self, tmp_path):
        """Different chat IDs must have separate memory."""
        from nexus_agent_platform.agents import nova
        original_dir = nova.MEMORY_DIR
        nova.MEMORY_DIR = str(tmp_path)
        try:
            nova.save_memory(11111, [{"role": "user", "content": "chat one"}])
            nova.save_memory(22222, [{"role": "user", "content": "chat two"}])
            mem1 = nova.load_memory(11111)
            mem2 = nova.load_memory(22222)
            assert mem1[0]["content"] == "chat one"
            assert mem2[0]["content"] == "chat two"
        finally:
            nova.MEMORY_DIR = original_dir

    def test_bounded_history(self, tmp_path):
        """Memory must not exceed max turns."""
        from nexus_agent_platform.agents import nova
        original_dir = nova.MEMORY_DIR
        nova.MEMORY_DIR = str(tmp_path)
        try:
            messages = []
            for i in range(50):
                messages.extend([
                    {"role": "user", "content": f"q{i}"},
                    {"role": "assistant", "content": f"a{i}"},
                ])
            nova.save_memory(99997, messages)
            loaded = nova.load_memory(99997)
            assert len(loaded) <= nova.MEMORY_MAX_TURNS * 2
        finally:
            nova.MEMORY_DIR = original_dir

    def test_empty_memory_returns_empty(self, tmp_path):
        from nexus_agent_platform.agents import nova
        original_dir = nova.MEMORY_DIR
        nova.MEMORY_DIR = str(tmp_path)
        try:
            loaded = nova.load_memory(99996)
            assert loaded == []
        finally:
            nova.MEMORY_DIR = original_dir


class TestResponseValidation:
    """Verify response validation catches issues."""

    def test_valid_response(self):
        from nexus_agent_platform.agents.nova import validate_response
        assert validate_response("Hello! How can I help you today?", "hi") is None

    def test_empty_response(self):
        from nexus_agent_platform.agents.nova import validate_response
        assert validate_response("", "hi") == "empty_response"
        assert validate_response("  ", "hi") == "empty_response"

    def test_provider_exception(self):
        from nexus_agent_platform.agents.nova import validate_response
        assert validate_response("Error: rate limit exceeded", "test") == "provider_exception"

    def test_system_prompt_leak(self):
        from nexus_agent_platform.agents.nova import validate_response
        assert validate_response("You are Hermes, a system designed to...", "test") == "system_prompt_leak"

    def test_false_tool_claim(self):
        from nexus_agent_platform.agents.nova import validate_response
        assert validate_response("I accessed your Supabase database", "query") == "false_tool_claim"

    def test_false_nexus_claim(self):
        from nexus_agent_platform.agents.nova import validate_response
        assert validate_response("I'll create a new user account", "status") == "false_nexus_claim"

    def test_capability_menu(self):
        from nexus_agent_platform.agents.nova import validate_response
        assert validate_response("Here is a list of my capabilities", "help") == "capability_menu"

    def test_leaked_bot_token(self):
        from nexus_agent_platform.agents.nova import validate_response
        # Telegram bot token: 10 digits : 35 alphanumeric chars
        token = "1234567890:" + "A" * 35
        assert validate_response(f"Token: {token}", "test") == "leaked_secret"

    def test_leaked_api_key(self):
        from nexus_agent_platform.agents.nova import validate_response
        assert validate_response("Key: sk-or-v1-abcdefghijklmnopqrstuv", "test") == "leaked_secret"


class TestGraphStructure:
    """Verify Nova graph is correctly structured."""

    def test_graph_builds(self):
        from nexus_agent_platform.agents.nova import get_nova_graph
        graph = get_nova_graph()
        assert graph._compiled is True

    def test_all_nodes_registered(self):
        from nexus_agent_platform.agents.nova import get_nova_graph
        graph = get_nova_graph()
        expected = ["pre_model_boundary", "build_context", "generate_response",
                    "validate_output", "compose_output"]
        assert list(graph._node_fns.keys()) == expected

    def test_entry_and_finish_points(self):
        from nexus_agent_platform.agents.nova import get_nova_graph
        graph = get_nova_graph()
        assert graph._entry_point == "pre_model_boundary"

    def test_agent_id(self):
        from nexus_agent_platform.agents.nova import AGENT_ID
        assert AGENT_ID == "hermes_nova"


class TestModelConfiguration:
    """Verify model configuration is correct."""

    def test_default_model(self):
        from nexus_agent_platform.agents.nova import DEFAULT_MODEL
        assert DEFAULT_MODEL == "openai/gpt-4o-mini"

    def test_model_timeout(self):
        from nexus_agent_platform.agents.nova import MODEL_TIMEOUT
        assert MODEL_TIMEOUT == 60

    def test_max_retries(self):
        from nexus_agent_platform.agents.nova import MAX_RETRIES
        assert MAX_RETRIES == 1

    def test_temperature(self):
        from nexus_agent_platform.agents.nova import DEFAULT_TEMPERATURE
        assert 0.0 <= DEFAULT_TEMPERATURE <= 1.0

    def test_max_tokens(self):
        from nexus_agent_platform.agents.nova import DEFAULT_MAX_TOKENS
        assert DEFAULT_MAX_TOKENS == 1024


class TestFeatureFlag:
    """Verify Nova has a feature flag."""

    def test_flag_exists(self):
        from nexus_agent_platform.flags import HERMES_NOVA_ENABLED
        assert isinstance(HERMES_NOVA_ENABLED, bool)

    def test_flag_in_status(self):
        from nexus_agent_platform.flags import status
        flags = status()
        assert "HERMES_NOVA_ENABLED" in flags


class TestIsolation:
    """Verify Nova does not import or depend on external services."""

    def test_no_supabase_import(self):
        """Nova must not import Supabase."""
        modules_before = set(sys.modules.keys())
        to_remove = [m for m in sys.modules if m.startswith("nexus_agent_platform.agents.nova")]
        for m in to_remove:
            del sys.modules[m]
        import nexus_agent_platform.agents.nova
        modules_after = set(sys.modules.keys())
        new_modules = modules_after - modules_before
        supabase = [m for m in new_modules if "supabase" in m]
        assert not supabase, f"Nova imported supabase: {supabase}"

    def test_no_oanda_import(self):
        """Nova must not import Oanda."""
        modules_before = set(sys.modules.keys())
        to_remove = [m for m in sys.modules if m.startswith("nexus_agent_platform.agents.nova")]
        for m in to_remove:
            del sys.modules[m]
        import nexus_agent_platform.agents.nova
        modules_after = set(sys.modules.keys())
        new_modules = modules_after - modules_before
        oanda = [m for m in new_modules if "oanda" in m]
        assert not oanda, f"Nova imported oanda: {oanda}"

    def test_no_temporal_import(self):
        """Nova must not import Temporal."""
        modules_before = set(sys.modules.keys())
        to_remove = [m for m in sys.modules if m.startswith("nexus_agent_platform.agents.nova")]
        for m in to_remove:
            del sys.modules[m]
        import nexus_agent_platform.agents.nova
        modules_after = set(sys.modules.keys())
        new_modules = modules_after - modules_before
        temporal = [m for m in new_modules if "temporal" in m]
        assert not temporal, f"Nova imported temporal: {temporal}"


class TestFallbackBehavior:
    """Verify degraded mode responses."""

    def test_fallback_empty(self):
        from nexus_agent_platform.agents.nova import _build_fallback_response
        resp = _build_fallback_response("empty_response", "test")
        assert "rephrase" in resp.lower() or "try" in resp.lower()

    def test_fallback_provider_error(self):
        from nexus_agent_platform.agents.nova import _build_fallback_response
        resp = _build_fallback_response("provider_exception", "test")
        assert "trouble" in resp.lower() or "error" in resp.lower() or "try" in resp.lower()

    def test_fallback_tool_claim(self):
        from nexus_agent_platform.agents.nova import _build_fallback_response
        resp = _build_fallback_response("false_tool_claim", "test")
        assert "don't have access" in resp.lower() or "nova" in resp.lower()


class TestPrewarmIntegration:
    """Verify Nova works with the prewarm function."""

    def test_prewarm_does_not_break_nova(self):
        from nexus_agent_platform.adapters.graph_adapter import prewarm_langgraph
        # Prewarm should not crash or affect Nova
        result = prewarm_langgraph()
        assert result["status"] in ("ok", "already_prewarmed", "import_failed")


class TestResetAtomicity:
    """Verify reset skips memory save in compose_output."""

    def test_compose_output_skips_save_on_reset(self, tmp_path):
        from nexus_agent_platform.agents import nova
        from nexus_agent_platform.adapters.state_adapter import AgentState

        original_dir = nova.MEMORY_DIR
        nova.MEMORY_DIR = str(tmp_path)
        try:
            # Pre-populate memory
            nova.save_memory(55555, [{"role": "user", "content": "old"}])

            # Simulate graph output with reset_requested
            state = AgentState(
                agent_id="hermes_nova",
                mission_id="test_mission",
                user_message="reset conversation",
                assistant_response="Memory cleared.",
                metadata={"chat_id": 55555, "reset_requested": True},
            )
            result = nova._compose_output(state)

            # Memory file should still contain OLD data (reset didn't overwrite)
            loaded = nova.load_memory(55555)
            assert len(loaded) == 1
            assert loaded[0]["content"] == "old"
        finally:
            nova.MEMORY_DIR = original_dir

    def test_reset_actual_deletion(self, tmp_path):
        """Worker-side reset_memory deletes the file after graph completes."""
        from nexus_agent_platform.agents import nova

        original_dir = nova.MEMORY_DIR
        nova.MEMORY_DIR = str(tmp_path)
        try:
            nova.save_memory(66666, [{"role": "user", "content": "will be deleted"}])
            nova.reset_memory(66666)
            loaded = nova.load_memory(66666)
            assert len(loaded) == 0
        finally:
            nova.MEMORY_DIR = original_dir


class TestDeliveryLock:
    """Verify per-chat lock prevents duplicate delivery."""

    def test_lock_acquire_release(self, tmp_path):
        """Lock can be acquired and released."""
        import sys
        # Import the worker module functions
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nova"))
        import nova_telegram_worker as nw

        # Override the state dir to temp
        original_dir = nw.NOVA_STATE_DIR
        nw.NOVA_STATE_DIR = str(tmp_path)
        try:
            lock = nw._acquire_chat_lock(77777)
            assert lock is not None
            assert os.path.exists(lock)
            nw._release_chat_lock(77777)
            assert not os.path.exists(lock)
        finally:
            nw.NOVA_STATE_DIR = original_dir

    def test_lock_prevents_double_acquire(self, tmp_path):
        """Second acquire fails while first lock is held."""
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "nova"))
        import nova_telegram_worker as nw
        original_dir = nw.NOVA_STATE_DIR
        nw.NOVA_STATE_DIR = str(tmp_path)
        try:
            lock1 = nw._acquire_chat_lock(88888)
            assert lock1 is not None
            lock2 = nw._acquire_chat_lock(88888)
            assert lock2 is None  # Should fail
            nw._release_chat_lock(88888)
        finally:
            nw.NOVA_STATE_DIR = original_dir


class TestSoulQuality:
    """Verify SOUL has quality guidance for technical and business advice."""

    def test_soul_mentions_technical_explanations(self):
        from nexus_agent_platform.agents.nova import SOUL
        soul_lower = SOUL.lower()
        assert "technical" in soul_lower or "architecture" in soul_lower

    def test_soul_mentions_business_advice(self):
        from nexus_agent_platform.agents.nova import SOUL
        soul_lower = SOUL.lower()
        assert "business" in soul_lower or "recommendation" in soul_lower

    def test_soul_mentions_quantify(self):
        from nexus_agent_platform.agents.nova import SOUL
        soul_lower = SOUL.lower()
        assert "quantify" in soul_lower or "costs" in soul_lower or "timelines" in soul_lower

    def test_soul_mentions_direct_judgment(self):
        from nexus_agent_platform.agents.nova import SOUL
        soul_lower = SOUL.lower()
        assert "direct" in soul_lower or "judgment" in soul_lower


class TestSemanticRouting:
    """Phase 20: Test that runtime-focused questions route correctly."""

    def _get_gate(self, text):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        return _semantic_capability_gate(text)

    def test_what_processes_routes_to_process_registry(self):
        cap, _ = self._get_gate("What processes exist?")
        assert cap == "get_process_registry"

    def test_what_is_running_routes_to_process_registry(self):
        cap, _ = self._get_gate("What is running right now?")
        assert cap == "get_process_registry"

    def test_actually_running_routes_to_process_registry(self):
        cap, _ = self._get_gate("Which processes are actually running right now?")
        assert cap == "get_process_registry"

    def test_currently_executing_routes_to_process_registry(self):
        cap, _ = self._get_gate("Is anything currently executing?")
        assert cap == "get_process_registry"

    def test_enabled_but_not_running_routes_to_process_registry(self):
        cap, _ = self._get_gate("Which processes are enabled but not running?")
        assert cap == "get_process_registry"

    def test_simulated_processes_routes_to_process_registry(self):
        cap, _ = self._get_gate("Which processes are only simulated?")
        assert cap == "get_process_registry"

    def test_what_failed_routes_to_recent_activity(self):
        cap, _ = self._get_gate("What failed today?")
        assert cap == "get_recent_activity"

    def test_what_happened_today_routes_to_recent_activity(self):
        cap, _ = self._get_gate("What happened in Nexus today?")
        assert cap == "get_recent_activity"

    def test_anything_pending_approval_routes_to_pending_approvals(self):
        cap, _ = self._get_gate("Do I have anything pending approval?")
        assert cap == "get_pending_approvals"

    def test_incomplete_areas_routes_correctly(self):
        cap, _ = self._get_gate("What parts of Nexus are incomplete?")
        assert cap == "get_incomplete_areas"

    def test_what_tools_routes_to_tool_registry(self):
        cap, _ = self._get_gate("What tools does Nexus have?")
        assert cap == "get_tool_registry"


class TestProcessDimensionSemantics:
    """Phase 18+: Verify process dimensions are semantically correct."""

    def test_enabled_count_plus_disabled_equals_total(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_process_registry_live
        result = get_process_registry_live()
        config = result["configuration_counts"]
        assert config.get("enabled", 0) + config.get("disabled", 0) == result["total"]

    def test_has_real_execution_false_when_all_simulated(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_process_registry_live
        result = get_process_registry_live()
        if result["all_simulated_or_skipped"]:
            assert result["has_real_execution"] is False

    def test_process_details_uses_normalized_fields(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_process_details
        result = get_process_details("daily_monitor")
        assert "configuration_state" in result
        assert "execution_mode" in result
        assert "runtime_state" in result
        assert "enabled" not in result  # raw field should not be exposed
        assert "mode" not in result  # raw field should not be exposed
        assert "last_status" not in result  # raw field should not be exposed


class TestComparativeRouting:
    """Phase 16: Test comparative process queries route correctly."""

    def _get_gate(self, text):
        from nexus_agent_platform.agents.nova import _semantic_capability_gate
        return _semantic_capability_gate(text)

    def test_enabled_but_not_actually_executing(self):
        cap, _ = self._get_gate("Which processes are enabled but not actually executing?")
        assert cap == "get_process_registry"

    def test_enabled_but_not_executing(self):
        cap, _ = self._get_gate("Which processes are enabled but not executing?")
        assert cap == "get_process_registry"

    def test_configured_but_not_running(self):
        cap, _ = self._get_gate("Which configured processes are not running?")
        assert cap == "get_process_registry"

    def test_configured_but_inactive(self):
        cap, _ = self._get_gate("Which processes are configured but inactive?")
        assert cap == "get_process_registry"

    def test_enabled_but_simulated(self):
        cap, _ = self._get_gate("Which enabled processes are simulated?")
        assert cap == "get_process_registry"

    def test_enabled_but_skipped(self):
        cap, _ = self._get_gate("Which enabled processes are skipped?")
        assert cap == "get_process_registry"

    def test_not_running_even_though_enabled(self):
        cap, _ = self._get_gate("Which processes are not running even though enabled?")
        assert cap == "get_process_registry"

    def test_active_in_config_but_not_live(self):
        cap, _ = self._get_gate("Which processes are active in config but not live?")
        assert cap == "get_process_registry"


class TestBlockedDimensions:
    """Phase 17: Test blocked dimension separation."""

    def test_process_registry_has_distinct_blocked(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_process_registry_live
        result = get_process_registry_live()
        runtime_blocked = result["runtime_counts"].get("blocked", 0)
        mode_blocked = result["mode_counts"].get("BLOCKED", 0)
        # These are independent dimensions — they may differ
        assert isinstance(runtime_blocked, int)
        assert isinstance(mode_blocked, int)

    def test_telegram_operator_is_skipped_not_simulated(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_process_registry_live
        result = get_process_registry_live()
        for p in result["processes"]:
            if p["process_id"] == "telegram_operator":
                assert p["runtime_state"] == "skipped"
                assert p["runtime_state"] != "simulated"

    def test_disabled_processes_have_correct_config_state(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_process_registry_live
        result = get_process_registry_live()
        disabled = [p for p in result["processes"] if p["configuration_state"] == "disabled"]
        assert len(disabled) == result["configuration_counts"].get("disabled", 0)
        for p in disabled:
            assert p["process_id"] in ("stripe_test_paywall", "client_portal_paywall_access")


class TestIncompleteCategoryIntegrity:
    """Phase 18: Test incomplete category count/item consistency."""

    def test_simulated_count_equals_items(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_incomplete_areas
        result = get_incomplete_areas()
        sim = result["categories"].get("simulated", {})
        assert sim.get("count", 0) == len(sim.get("items", []))

    def test_dry_run_count_equals_items(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_incomplete_areas
        result = get_incomplete_areas()
        dr = result["categories"].get("dry_run", {})
        assert dr.get("count", 0) == len(dr.get("items", []))

    def test_unavailable_tools_count_equals_items(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_incomplete_areas
        result = get_incomplete_areas()
        ut = result["categories"].get("unavailable_tools", {})
        assert ut.get("count", 0) == len(ut.get("items", []))

    def test_skipped_not_in_simulated(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_incomplete_areas
        result = get_incomplete_areas()
        sim_items = result["categories"].get("simulated", {}).get("items", [])
        # Telegram Operator is skipped, not simulated — should not appear in simulated
        assert "Telegram Operator" not in sim_items

    def test_unique_count_deduplication(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_incomplete_areas
        result = get_incomplete_areas()
        unique = result["unique_incomplete_count"]
        cat_sum = sum(result["category_counts"].values())
        assert unique <= cat_sum


class TestSourceClassification:
    """Phase 19: Test source classification model."""

    def test_process_registry_has_source_classification(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_process_registry_live
        result = get_process_registry_live()
        # Process registry is structural/configuration
        assert result["source_type"] == "process_registry"

    def test_incomplete_areas_is_registry_derived(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_incomplete_areas
        result = get_incomplete_areas()
        assert result["source_type"] == "registry_derived"

    def test_approval_queue_is_operational_state(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_recent_activity_live
        result = get_recent_activity_live()
        approvals = result["components"].get("approvals", {})
        # Approvals are operational state, not structural
        assert approvals.get("status") in ("success", "unavailable", "error")

    def test_all_simulated_implies_no_execution_telemetry(self):
        from nexus_agent_platform.capabilities.nexus_knowledge import get_process_registry_live
        result = get_process_registry_live()
        if result["all_simulated_or_skipped"]:
            assert result["has_real_execution"] is False
