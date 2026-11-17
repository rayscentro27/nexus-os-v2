from __future__ import annotations


def test_dispatcher_control_plane_egress_window_is_unique_per_process_invocation(monkeypatch):
    from nexus_agent_platform import dispatcher_once

    monkeypatch.delenv("NEXUS_DURABLE_EXECUTION_ID", raising=False)
    dispatcher_once._initialize_dispatch_egress_context()
    first = __import__("os").environ["NEXUS_DURABLE_EXECUTION_ID"]
    assert first.startswith(f"dispatcher-{__import__('os').getpid()}-")

    # The initialized context remains stable for this invocation; the next
    # dispatcher process receives a fresh ID and cannot inherit PID-era counts.
    dispatcher_once._initialize_dispatch_egress_context()
    assert __import__("os").environ["NEXUS_DURABLE_EXECUTION_ID"] == first
