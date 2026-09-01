from services.google_mcp import server


def test_google_surface_is_granular_and_read_only():
    names = {tool.name for tool in server.mcp._tool_manager.list_tools()}
    assert names == set(server.TOOL_NAMES)
    assert not names & {"gmail_send", "gmail_reply", "calendar_create_event", "calendar_update_event", "calendar_delete_event"}


def test_message_summary_is_bounded_and_header_only():
    value = server._message_summary({
        "id": "m1", "threadId": "t1", "internalDate": "1",
        "snippet": "short excerpt", "labelIds": ["INBOX"],
        "payload": {"headers": [
            {"name": "Subject", "value": "Hello"},
            {"name": "From", "value": "sender@example.com"},
            {"name": "Ignored", "value": "not exposed"},
        ]},
    })
    assert value["headers"] == {"subject": "Hello", "from": "sender@example.com"}
    assert "body" not in value


def test_event_summary_excludes_unnecessary_description():
    value = server._event_summary({
        "id": "e1", "summary": "Meeting", "description": "private details",
        "status": "confirmed", "start": {"dateTime": "2026-09-01T10:00:00-07:00"},
        "end": {"dateTime": "2026-09-01T11:00:00-07:00"},
    })
    assert value["summary"] == "Meeting"
    assert "description" not in value


def test_google_failure_is_truthful_and_read_only(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "RECEIPT_DIR", tmp_path)
    monkeypatch.setattr(server, "_credentials", lambda: (_ for _ in ()).throw(RuntimeError("offline")))
    result = server.gmail_search("newer_than:1d", 1)
    assert result["status"] == "error"
    assert result["items"] == []
    assert result["read_only"] is True
