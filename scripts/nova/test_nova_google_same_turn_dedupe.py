import json
import sys
import types

from nova_hermes_shadow import _GOOGLE_DEDUPE_EVENTS, _install_google_turn_dedupe


class _Entry:
    handler = None


class _FakeRegistry:
    def __init__(self):
        self._tools = {}
        self.calls = []

    def dispatch(self, name, args, **kwargs):
        self.calls.append((name, dict(args), dict(kwargs)))
        return json.dumps({"status": "ok", "query": args.get("query")})


def _install_for(fake):
    tools_module = types.ModuleType("tools")
    registry_module = types.ModuleType("tools.registry")
    registry_module.registry = fake
    tools_module.registry = registry_module
    old_tools = sys.modules.get("tools")
    old_registry = sys.modules.get("tools.registry")
    sys.modules["tools"] = tools_module
    sys.modules["tools.registry"] = registry_module
    try:
        _install_google_turn_dedupe()
    finally:
        if old_tools is None:
            sys.modules.pop("tools", None)
        else:
            sys.modules["tools"] = old_tools
        if old_registry is None:
            sys.modules.pop("tools.registry", None)
        else:
            sys.modules["tools.registry"] = old_registry


def test_equivalent_gmail_search_reuses_successful_result_across_continuations():
    fake = _FakeRegistry()
    _install_for(fake)
    first = fake.dispatch("mcp__google_mcp__gmail_search", {"query": " is:unread ", "max_results": 5}, task_id="shadow-turn-dedupe")
    second = fake.dispatch("mcp__google_mcp__gmail_search", {"query": "IS:UNREAD", "max_results": 25}, task_id="shadow-turn-dedupe-evidence")
    assert first == second
    assert len(fake.calls) == 1
    events = _GOOGLE_DEDUPE_EVENTS["shadow-turn-dedupe"]
    assert [event["dedupe_decision"] for event in events] == ["EXECUTE", "REUSED_SUCCESS"]


def test_distinct_gmail_searches_and_cross_turn_reads_remain_independent():
    fake = _FakeRegistry()
    _install_for(fake)
    fake.dispatch("mcp__google_mcp__gmail_search", {"query": "is:unread"}, task_id="turn-a")
    fake.dispatch("mcp__google_mcp__gmail_search", {"query": "from:supabase.com"}, task_id="turn-a")
    fake.dispatch("mcp__google_mcp__gmail_search", {"query": "is:unread"}, task_id="turn-b")
    assert len(fake.calls) == 3


def test_failed_first_call_is_not_cached_as_success():
    fake = _FakeRegistry()
    attempts = {"count": 0}

    def dispatch(name, args, **kwargs):
        attempts["count"] += 1
        fake.calls.append((name, dict(args), dict(kwargs)))
        return json.dumps({"error": "temporary"}) if attempts["count"] == 1 else json.dumps({"status": "ok"})

    fake.dispatch = dispatch
    _install_for(fake)
    fake.dispatch("mcp__google_mcp__gmail_search", {"query": "is:unread"}, task_id="turn-fail")
    fake.dispatch("mcp__google_mcp__gmail_search", {"query": "is:unread"}, task_id="turn-fail")
    fake.dispatch("mcp__google_mcp__gmail_search", {"query": "is:unread"}, task_id="turn-fail")
    assert attempts["count"] == 2
