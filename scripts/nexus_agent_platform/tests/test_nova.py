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
        assert validate_response("I'll check the process registry", "status") == "false_nexus_claim"

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
        expected = ["classify_intent", "handle_utility", "build_context",
                    "generate_response", "validate_output", "compose_output"]
        assert list(graph._node_fns.keys()) == expected

    def test_entry_and_finish_points(self):
        from nexus_agent_platform.agents.nova import get_nova_graph
        graph = get_nova_graph()
        assert graph._entry_point == "classify_intent"

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
        assert result["status"] in ("ok", "already_prewarmed")
