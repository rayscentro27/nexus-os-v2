"""Bounded shadow room worker and idempotent next-turn job planner."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from .models import ResearchCase, new_case
from .room_graph import RoomGraph
from .state import JsonCaseStore


class ResearchRoomWorker:
    def __init__(self, store: JsonCaseStore, graph: RoomGraph):
        self.store, self.graph = store, graph

    def open_case(self, *, case_id: str, objective: str, source_url: str | None = None,
                  source_type: str = "UNKNOWN", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        current = self.store.load(case_id)
        if current:
            return current
        case = new_case(case_id, objective, source_url, source_type, metadata)
        case.turn_jobs.append(self._make_job(case, sequence=0, participant="RESEARCH_LEAD"))
        return self.store.save(case)

    @staticmethod
    def _make_job(state: dict[str, Any], *, sequence: int, participant: str) -> dict[str, Any]:
        case_id = state.case_id if hasattr(state, "case_id") else state["case_id"]
        key_material = f"{case_id}:{sequence}:{participant}"
        return {"job_type": "RESEARCH_ROOM_TURN", "case_id": case_id,
            "participant": participant, "sequence": sequence,
            "idempotency_key": "rrt_" + hashlib.sha256(key_material.encode()).hexdigest()[:24],
            "state": "READY", "shadow_mode": True}

    def run_turn_job(self, job: dict[str, Any]) -> dict[str, Any]:
        case_id = str(job["case_id"])
        state = self.store.load(case_id)
        if state is None:
            raise KeyError(f"RESEARCH_ROOM_CASE_NOT_FOUND:{case_id}")
        key = str(job["idempotency_key"])
        if key in state.get("processed_turns", {}):
            receipt = dict(state["processed_turns"][key])
            receipt["case"] = state
            return receipt
        if state.get("status") == "COMPLETE":
            return {"status": "COMPLETE", "case": state, "next_job": None}
        if int(job.get("sequence", -1)) != int(state.get("turn_count", 0)):
            raise RuntimeError("STALE_OR_OUT_OF_ORDER_RESEARCH_ROOM_TURN")
        if str(job.get("participant")) != str(state.get("next_participant")):
            raise RuntimeError("RESEARCH_ROOM_TURN_PARTICIPANT_MISMATCH")
        stored_job = next((row for row in state.get("turn_jobs", []) if row.get("idempotency_key") == key), None)
        if not stored_job or stored_job.get("state") not in {"READY", "RUNNING"}:
            raise RuntimeError("RESEARCH_ROOM_TURN_JOB_NOT_CLAIMABLE")
        stored_job["state"] = "RUNNING"
        before_turn = int(state.get("turn_count", 0))
        updated = self.graph.turn(state)
        if int(updated.get("turn_count", 0)) != before_turn + 1:
            raise RuntimeError("ROOM_TURN_MUST_EXECUTE_EXACTLY_ONE_PARTICIPANT")
        updated_job = next(row for row in updated["turn_jobs"] if row.get("idempotency_key") == key)
        updated_job["state"] = "COMPLETED"
        next_job = None
        if updated.get("status") != "COMPLETE":
            sequence = int(updated.get("turn_count", 0))
            next_job = self._make_job(updated, sequence=sequence,
                                      participant=str(updated.get("next_participant")))
            if not any(row.get("idempotency_key") == next_job["idempotency_key"] for row in updated["turn_jobs"]):
                updated["turn_jobs"].append(next_job)
        result = {"status": updated.get("status"), "executed_participant": job.get("participant"),
                  "case": updated, "next_job": next_job}
        updated.setdefault("processed_turns", {})[key] = {"status": result["status"],
            "executed_participant": result["executed_participant"], "case_id": case_id,
            "next_job": next_job}
        if updated.get("status") == "COMPLETE":
            from .transcripts import write_case_artifacts
            transcript_root = (updated.get("metadata") or {}).get("transcript_root") or os.getenv(
                "NEXUS_RESEARCH_ROOM_TRANSCRIPT_DIR", str(Path.home() / ".nexus/research_room/transcripts"))
            paths = write_case_artifacts(updated, transcript_root)
            updated.setdefault("metadata", {})["transcript_paths"] = paths
            result["case"] = updated
        self.store.save(ResearchCase.from_dict(updated))
        return result

    def run_one_turn(self, case_id: str) -> dict[str, Any]:
        state = self.store.load(case_id)
        if state is None:
            raise KeyError(f"RESEARCH_ROOM_CASE_NOT_FOUND:{case_id}")
        ready = next((row for row in state.get("turn_jobs", []) if row.get("state") == "READY"), None)
        if ready is None:
            if state.get("status") == "COMPLETE":
                return {"status": "COMPLETE", "case": state, "next_job": None}
            raise RuntimeError("NO_READY_RESEARCH_ROOM_TURN")
        return self.run_turn_job(ready)
        return {"status": updated.get("status"), "executed_participant": state.get("next_participant"),
                "case": updated, "next_job": next_job}


class ShadowRoomRunner:
    """Test/report helper; advances separately bounded worker turns locally."""
    def __init__(self, worker: ResearchRoomWorker, max_turns: int = 20):
        self.worker, self.max_turns = worker, max_turns

    def run_to_completion(self, case_id: str) -> dict[str, Any]:
        turns, job_keys = [], set()
        for _ in range(self.max_turns):
            result = self.worker.run_one_turn(case_id)
            turns.append({"participant": result.get("executed_participant"), "status": result["status"]})
            job = result.get("next_job")
            if job:
                if job["idempotency_key"] in job_keys:
                    raise RuntimeError("DUPLICATE_ROOM_TURN_JOB")
                job_keys.add(job["idempotency_key"])
            if result["status"] == "COMPLETE":
                return {"status": "COMPLETE", "case": result["case"], "turns": turns,
                    "continuation_jobs_planned": len(job_keys)}
        return {"status": "INCOMPLETE", "case": self.worker.store.load(case_id), "turns": turns,
                "continuation_jobs_planned": len(job_keys)}
