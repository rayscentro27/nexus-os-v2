"""Mission model — tracks agent missions through their lifecycle.

Mission lifecycle:
  RECEIVED → AUTHORIZED → ROUTED → EXECUTING → RESULT_STORED →
  RESPONSE_COMPOSED → RESPONSE_SENT → COMPLETED

Missions are separate per agent and stored in data/missions/.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


from nexus_agent_platform.runtime.paths import get_nexus_repo_root

_MISSIONS_DIR = str(get_nexus_repo_root() / "data" / "missions")


def _ensure_dir(agent_id: str) -> str:
    path = os.path.join(_MISSIONS_DIR, agent_id)
    os.makedirs(path, exist_ok=True)
    return path


@dataclass
class Mission:
    mission_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    agent_id: str = ""
    status: str = "RECEIVED"
    user_message: str = ""
    result: Optional[str] = None
    telegram_message_id: Optional[int] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.save()

    def save(self) -> None:
        d = _ensure_dir(self.agent_id)
        path = os.path.join(d, f"{self.mission_id}.json")
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2, default=str)

    @classmethod
    def load(cls, agent_id: str, mission_id: str) -> Optional["Mission"]:
        path = os.path.join(_ensure_dir(agent_id), f"{mission_id}.json")
        if not os.path.exists(path):
            return None
        with open(path) as f:
            return cls(**json.load(f))

    @classmethod
    def create(cls, agent_id: str, user_message: str = "", **kwargs: Any) -> "Mission":
        mission = cls(agent_id=agent_id, user_message=user_message, **kwargs)
        mission.save()
        return mission

    @classmethod
    def list_recent(cls, agent_id: str, limit: int = 10) -> list["Mission"]:
        d = _ensure_dir(agent_id)
        missions = []
        for fname in sorted(os.listdir(d), reverse=True)[:limit]:
            if fname.endswith(".json"):
                with open(os.path.join(d, fname)) as f:
                    missions.append(cls(**json.load(f)))
        return missions
