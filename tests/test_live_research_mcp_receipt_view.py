"""Default Research MCP output hides receipt internals but retains diagnostic opt-in."""
from __future__ import annotations

import asyncio
import importlib
import sys
from pathlib import Path

R5=Path.home()/".nexus/releases/nexus-research-mcp-v1-20261103-social-submission-r5"
sys.path.insert(0,str(R5))
server=importlib.import_module("research_mcp.server")


def test_status_hides_nested_receipts_and_keeps_queue_summary(monkeypatch):
    async def fake_request(*args,**kwargs):
        return server._receipt_view({"ok":True,"data":{"queue_summary":{"total_jobs":3},"jobs":[{"job_id":"job-secret","receipt":{"receipt_id":"rcpt-secret"}}]}},include_internal_receipts=kwargs.get("include_internal_receipts",False))
    monkeypatch.setattr(server,"_r10_request",fake_request)
    result=asyncio.run(server.research_status())
    assert result["data"]["queue_summary"]["total_jobs"]==3
    assert "receipt" not in result["data"]["jobs"][0]
    assert "job_id" in result["data"]["jobs"][0]


def test_result_receipt_is_available_only_on_explicit_diagnostic_request(monkeypatch):
    async def fake_request(*args,**kwargs):
        return server._receipt_view({"ok":True,"data":{"result":{"summary":"done","receipt":{"receipt_id":"rcpt-secret"}}}},include_internal_receipts=kwargs.get("include_internal_receipts",False))
    monkeypatch.setattr(server,"_r10_request",fake_request)
    ordinary=asyncio.run(server.research_result("job-secret"))
    diagnostic=asyncio.run(server.research_result("job-secret",include_internal_receipts=True))
    assert "receipt" not in ordinary["data"]["result"]
    assert diagnostic["data"]["result"]["receipt"]["receipt_id"]=="rcpt-secret"


def test_research_start_accepts_stable_reconciliation_key(monkeypatch):
    observed={}
    async def fake_request(operation,payload,**kwargs):
        observed.update(operation=operation,payload=payload)
        return {"ok":True,"data":{"accepted":True}}
    monkeypatch.setattr(server,"_r10_request",fake_request)
    result=asyncio.run(server.research_start(
        "Review current public guidance","GENERAL","NORMAL",
        ["https://example.org/official-guidance"],[],"legacy_projection_stable_key"))
    assert result["ok"]
    assert observed["operation"]=="start"
    assert observed["payload"]["idempotency_key"]=="legacy_projection_stable_key"
