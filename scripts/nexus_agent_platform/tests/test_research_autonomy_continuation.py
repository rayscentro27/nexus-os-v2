from nexus_agent_platform import research_lane_scheduler as scheduler


class EmptyQueue:
    def __init__(self):
        self.claimed = False

    def load(self):
        return {"items": []}

    def claim_next(self, **kwargs):
        self.claimed = True
        return {"work_id": "goal-objective-1", "status": "IN_PROGRESS"}


def test_empty_queue_invokes_purpose_continuation(monkeypatch):
    queue = EmptyQueue()
    monkeypatch.setattr(scheduler, "default_queue", lambda: queue)
    monkeypatch.setattr(scheduler, "ensure_registry", lambda: [])
    monkeypatch.setattr(scheduler, "ensure_live_program_work", lambda: {"created": []})
    monkeypatch.setattr(scheduler, "ensure_permanent_source_work", lambda: {"created": []})
    monkeypatch.setattr(scheduler, "_select_live_service_work", lambda *args, **kwargs: None)
    monkeypatch.setattr(scheduler, "select_priority_work", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        "nexus_agent_platform.research_continuation.continue_when_empty",
        lambda **kwargs: {"generated": [{"objective_id": "goal-objective-1"}]},
    )
    selected = scheduler.select_lane(reason="test_empty_queue")
    assert selected["work_id"] == "goal-objective-1"
    assert selected["selection_reason"] == "goal_generated"
    assert queue.claimed is True
