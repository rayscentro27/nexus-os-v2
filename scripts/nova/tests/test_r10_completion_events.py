from __future__ import annotations

import json
import sys

from nova import nexus_mcp_status as mcp_status
from nova import proactive_communications as proactive


def _event():
    return {
        "kind": "RESEARCH_COMPLETED",
        "event_type": "RESEARCH_COMPLETED",
        "source": "R10_COMPLETION_EVENT",
        "source_event_id": "event-private-id",
        "job_id": "job_private",
        "subject": "Trading Strategy Video Research",
        "title": "Trading Strategy Video Research — COMPLETED",
        "department": "Research",
        "status": "COMPLETED",
        "summary": "The video was summarized from its English captions.",
        "key_findings": ["The video describes backtesting and portfolio allocation."],
    }


def test_subject_first_research_notification_hides_internal_ids():
    message = proactive._message(_event(), "MATERIAL")
    assert message.startswith("Ray, Trading Strategy Video Research is complete.")
    assert "Department: Research" in message
    assert "event-private-id" not in message
    assert "job_" not in message


def test_r10_event_acknowledged_only_after_successful_telegram_delivery(tmp_path, monkeypatch):
    monkeypatch.setattr(proactive, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(proactive, "trusted_ray_chat", lambda: "trusted-chat")
    messages = []
    monkeypatch.setattr(proactive, "tg_send_message", lambda chat, text: messages.append(text) or [42])
    calls = []
    monkeypatch.setitem(sys.modules, "nexus_mcp_status", mcp_status)
    monkeypatch.setattr(mcp_status, "call_research_mcp_tool",
                        lambda tool, args: calls.append((tool, args)) or ({"acknowledged": args["event_ids"]}, 2))

    result = proactive.process_once(events=[_event()])

    assert result["status"] == "PASS"
    assert messages[0].startswith("Ray, Trading Strategy Video Research is complete.")
    assert calls == [("research_completion_ack", {"event_ids": ["event-private-id"]})]


def test_failed_telegram_delivery_leaves_r10_event_pending(tmp_path, monkeypatch):
    monkeypatch.setattr(proactive, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(proactive, "trusted_ray_chat", lambda: "trusted-chat")
    monkeypatch.setattr(proactive, "tg_send_message", lambda chat, text: None)
    calls = []
    monkeypatch.setitem(sys.modules, "nexus_mcp_status", mcp_status)
    monkeypatch.setattr(mcp_status, "call_research_mcp_tool",
                        lambda tool, args: calls.append((tool, args)) or ({}, 2))

    result = proactive.process_once(events=[_event()])

    assert result["status"] == "NO_SEND"
    assert calls == []


def test_collection_reads_without_consuming_and_fetches_full_completed_result(tmp_path, monkeypatch):
    monkeypatch.setattr(proactive, "HEARTBEAT_PATH", tmp_path / "heartbeat.json")
    monkeypatch.setattr(proactive, "OPERATOR_PATH", tmp_path / "operator.json")
    monkeypatch.setitem(sys.modules, "nexus_mcp_status", mcp_status)
    event = {**_event(), "job_id": "job-private", "event_id": "event-private-id"}
    calls = []

    def read(tool, arguments):
        calls.append((tool, arguments))
        if tool == "research_completion_events":
            return {"events": [event]}, 9
        return {"ok": True, "data": {
            "subject": "Trading Strategy Video Research",
            "status": "COMPLETED",
            "summary": "Verified summary from the saved Research result.",
            "key_findings": ["Finding from the full result."],
            "recommendation": "Run a bounded follow-up test.",
            "evidence_limitations": ["The source transcript did not include visual details."],
            "open_questions": ["Confirm current platform availability."],
        }}, 9

    monkeypatch.setattr(mcp_status, "call_research_mcp_tool", read)
    events = [item for item in proactive.collect_events() if item.get("source") == "R10_COMPLETION_EVENT"]

    assert calls == [
        ("research_completion_events", {"limit": 20}),
        ("research_result", {"job_id": "job-private"}),
    ]
    assert len(events) == 1
    assert events[0]["subject"] == "Trading Strategy Video Research"
    message = proactive._message(events[0], "MATERIAL")
    assert "Verified summary from the saved Research result." in message
    assert "Run a bounded follow-up test." in message
    assert "The source transcript did not include visual details." in message
    assert "Confirm current platform availability." in message
    assert "job-private" not in message and "event-private-id" not in message


def test_r10_event_dedup_uses_subject_and_suppresses_replayed_event(tmp_path, monkeypatch):
    monkeypatch.setattr(proactive, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(proactive, "trusted_ray_chat", lambda: "trusted-chat")
    sends = []
    monkeypatch.setattr(proactive, "tg_send_message", lambda chat, message: sends.append(message) or [len(sends)])
    monkeypatch.setitem(sys.modules, "nexus_mcp_status", mcp_status)
    ack_calls = []
    monkeypatch.setattr(mcp_status, "call_research_mcp_tool",
                        lambda tool, args: ack_calls.append((tool, args)) or ({"ok": True}, 9))
    first = {**_event(), "source_event_id": "event-a"}
    second = {**_event(), "subject": "Credit Plug Funding Research", "source_event_id": "event-b"}

    result = proactive.process_once(events=[first, second, first])

    assert result["status"] == "PASS"
    assert len(sends) == 2
    assert sends[0] != sends[1]
    assert any(x.get("status") == "SUPPRESSED_DUPLICATE" for x in result["results"])
    assert ack_calls == [("research_completion_ack", {"event_ids": ["event-a", "event-b"]})]


def test_financial_approval_and_terminal_failure_states_are_plain_language():
    approval = proactive._message({**_event(), "status": "WAITING_FOR_FINANCIAL_APPROVAL"}, "CRITICAL")
    failure = proactive._message({**_event(), "status": "FAILED_TERMINAL", "required_action": "Review the saved failure reason."}, "CRITICAL")
    assert approval.startswith("Ray, Trading Strategy Video Research is waiting for financial approval.")
    assert "Action needed:" not in approval
    assert failure.startswith("Ray, Trading Strategy Video Research failed.")
    assert "Blocker: Review the saved failure reason." in failure


def test_completed_event_is_left_pending_when_full_result_read_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(proactive, "HEARTBEAT_PATH", tmp_path / "heartbeat.json")
    monkeypatch.setattr(proactive, "OPERATOR_PATH", tmp_path / "operator.json")
    monkeypatch.setitem(sys.modules, "nexus_mcp_status", mcp_status)
    calls = []

    def read(tool, arguments):
        calls.append((tool, arguments))
        if tool == "research_completion_events":
            return {"events": [{**_event(), "job_id": "job-private"}]}, 9
        raise RuntimeError("result temporarily unavailable")

    monkeypatch.setattr(mcp_status, "call_research_mcp_tool", read)
    events = [item for item in proactive.collect_events() if item.get("source") == "R10_COMPLETION_EVENT"]

    assert events == []
    assert calls[-1] == ("research_result", {"job_id": "job-private"})



# --- NOVA_RESEARCH_NOTIFICATION_REPAIR_R1 (2026-11-14) -----------------------

def _outbox(*items):
    return {"ok": True, "data": {"events": list(items)}}


def _row(event_id, job_id, event="research.completed", status="COMPLETED", subject="Subject"):
    return {"event_id": event_id, "job_id": job_id, "event": event, "status": status,
            "subject": subject, "summary": "Outbox summary.", "receipt": {"kind": "RESEARCH_COMPLETE"}}


def _result(status="COMPLETED", **extra):
    return {"ok": True, "data": {"status": status, "subject": "Storage comparison",
            "summary": "Saved summary.", "key_findings": [{"text": "Finding one."}],
            "recommendation": {"decision": "Present the modified architecture to Ray.",
                               "execution_status": "Research only. Nothing deployed."},
            "open_questions": [{"question": "What is the actual workload?", "impact": "cost"}],
            "evidence_limitations": ["Research library access was rejected. Public official sources supplied the comparison.",
                                     "No workload measurements were available."],
            "evidence_references": ["src_a", "src_b", "src_c"],
            "receipt": {"kind": "RESEARCH_COMPLETE", "completed_at": "2026-11-14T00:48:27.559025+00:00",
                        "source_count": 3}, **extra}}


def _isolate(tmp_path, monkeypatch, reader):
    monkeypatch.setattr(proactive, "HEARTBEAT_PATH", tmp_path / "heartbeat.json")
    monkeypatch.setattr(proactive, "OPERATOR_PATH", tmp_path / "operator.json")
    monkeypatch.setattr(proactive, "RECEIPT_DIR", tmp_path / "receipts")
    monkeypatch.setattr(proactive, "MATERIAL_EVENTS_PATH", tmp_path / "material.jsonl")
    monkeypatch.setattr(proactive, "STATE_PATH", tmp_path / "state.json")
    monkeypatch.setattr(proactive, "FREEZE_PATH", tmp_path / "freeze")
    monkeypatch.setattr(proactive, "trusted_ray_chat", lambda: "trusted-chat")
    monkeypatch.setitem(sys.modules, "nexus_mcp_status", mcp_status)
    monkeypatch.setattr(mcp_status, "call_research_mcp_tool", reader)


def test_completed_with_limitations_head_event_no_longer_blocks(tmp_path, monkeypatch):
    def reader(tool, args):
        if tool == "research_completion_events":
            return _outbox(_row("event_lim", "job_lim", status="COMPLETED_WITH_LIMITATIONS")), 2
        return _result(status="COMPLETED_WITH_LIMITATIONS"), 2
    _isolate(tmp_path, monkeypatch, reader)
    research = [e for e in proactive.collect_events() if e.get("source") == "R10_COMPLETION_EVENT"]
    assert [e["source_event_id"] for e in research] == ["event_lim"]
    assert research[0]["status"] == "COMPLETED_WITH_LIMITATIONS"
    assert proactive._message(research[0], "MATERIAL").startswith("Ray, Storage comparison is complete, with limitations.")


def test_undeliverable_head_row_is_skipped_not_blocking(tmp_path, monkeypatch):
    def reader(tool, args):
        if tool == "research_completion_events":
            return _outbox(_row("event_bad", "job_bad"), _row("event_ok", "job_ok")), 2
        if args["job_id"] == "job_bad":
            raise RuntimeError("result unavailable")
        return _result(), 2
    _isolate(tmp_path, monkeypatch, reader)
    research = [e for e in proactive.collect_events() if e.get("source") == "R10_COMPLETION_EVENT"]
    assert [e["source_event_id"] for e in research] == ["event_ok"]  # one per cycle, bad row stays pending


def test_approval_required_notice_reads_saved_result_and_formats_for_owner(tmp_path, monkeypatch):
    def reader(tool, args):
        if tool == "research_completion_events":
            return _outbox(_row("event_cert", "job_cert", event="research.approval_required",
                                status="APPROVAL_REQUIRED")), 2
        return _result(), 2
    _isolate(tmp_path, monkeypatch, reader)
    event = [e for e in proactive.collect_events() if e.get("source") == "R10_COMPLETION_EVENT"][0]
    text = proactive._message(event, "MATERIAL")
    assert text.startswith("Ray, Storage comparison is complete and waiting for your approval.")  # no objective -> subject
    assert "Research completed at 5:48 PM Arizona time on Nov 13, 2026." in text
    assert ".559025" not in text and "2026-11-14T" not in text and "+00:00" not in text
    assert "Present the modified architecture to Ray. Research only. Nothing deployed." in text
    assert "{'decision'" not in text and "{'question'" not in text
    assert "What is the actual workload?" in text
    assert "official sources supplied" not in text.lower()
    assert "3 cited" in text and "unclassified" in text
    assert "job_cert" not in text and "event_cert" not in text


def test_explicit_source_classes_are_reported_without_calling_all_official():
    text = proactive._message({"source": "R10_COMPLETION_EVENT", "status": "COMPLETED", "subject": "S",
                               "summary": "x", "source_classes": {"official": 12, "secondary": 6, "community": 2}},
                              "MATERIAL")
    assert "Sources: 12 official/primary, 6 secondary, 2 community." in text


def test_owner_time_has_no_microseconds_and_uses_phoenix():
    assert proactive.owner_time("2026-11-14T00:48:27.559025+00:00") == "5:48 PM Arizona time on Nov 13, 2026"
    assert proactive.owner_time("2026-07-01T19:05:00Z") == "12:05 PM Arizona time on Jul 1, 2026"


def test_full_freeze_sends_acks_and_writes_nothing(tmp_path, monkeypatch):
    sends, calls = [], []
    _isolate(tmp_path, monkeypatch, lambda tool, args: calls.append(tool) or ({}, 2))
    monkeypatch.setattr(proactive, "tg_send_message", lambda chat, text: sends.append(text) or [1])
    (tmp_path / "freeze").write_text("{}")
    result = proactive.process_once(events=[_event()])
    assert result == {"status": "NO_SEND", "frozen": True, "results": []}
    assert sends == [] and calls == [] and not (tmp_path / "state.json").exists()


def test_allowlisted_freeze_delivers_exactly_one_event_then_replay_is_suppressed(tmp_path, monkeypatch):
    sends, acks = [], []

    def reader(tool, args):
        if tool == "research_completion_ack":
            acks.append(args["event_ids"])
            return {"acknowledged": args["event_ids"]}, 2
        if tool == "research_completion_events":
            return _outbox(_row("event_other", "job_other"), _row("event_cert", "job_cert",
                           event="research.approval_required", status="APPROVAL_REQUIRED")), 2
        return _result(), 2
    _isolate(tmp_path, monkeypatch, reader)
    monkeypatch.setattr(proactive, "tg_send_message", lambda chat, text: sends.append(text) or [77])
    (tmp_path / "freeze").write_text(json.dumps({"allow_event_ids": ["event_cert"]}))
    first = proactive.process_once()
    assert first["status"] == "PASS" and len(sends) == 1 and acks == [["event_cert"]]
    second = proactive.process_once()
    assert second["status"] == "NO_SEND" and len(sends) == 1
    assert second["results"][0]["status"] == "SUPPRESSED_DUPLICATE"


def test_approval_blocked_failed_r10_notices_are_deliverable_not_suppressed(tmp_path, monkeypatch):
    sends = []
    _isolate(tmp_path, monkeypatch, lambda tool, args: ({"acknowledged": args.get("event_ids", [])}, 2))
    monkeypatch.setattr(proactive, "tg_send_message", lambda chat, text: sends.append(text) or [5])
    for kind, status in (("RESEARCH_APPROVAL_REQUIRED", "APPROVAL_REQUIRED"), ("RESEARCH_BLOCKED", "BLOCKED"),
                         ("RESEARCH_FAILED", "FAILED_TERMINAL")):
        event = {**_event(), "kind": kind, "event_type": kind, "status": status,
                 "subject": f"Subject {kind}", "source_event_id": f"event_{kind}"}
        assert proactive._severity(event) == "MATERIAL"
        assert proactive.process_once(events=[event])["status"] == "PASS"
    assert len(sends) == 3


def test_owner_label_prefers_objective_over_source_title_but_keeps_video_titles():
    objective = ("Compare Cloudflare R2, Supabase Storage and Modal for the Nexus Content Library "
                 "and determine the recommended production role for each.")
    assert proactive._owner_label(objective, "Presigned URLs · Cloudflare R2 docs") == objective.rstrip(".")
    assert proactive._owner_label("Research the newly published YouTube item and summarize it.",
                                  "Most men need to hear this") == "Most men need to hear this"
    assert proactive._owner_label("", "Fallback subject") == "Fallback subject"
    long = "Research current pricing " + "and plans " * 40 + ". Use official pages."
    assert len(proactive._owner_label(long, "x")) <= 161
