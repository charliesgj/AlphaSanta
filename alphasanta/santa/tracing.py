"""
Workflow tracing utilities for visualizing Santa's decision process.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class WorkflowEvent:
    """
    Represents a single step in the Santa workflow timeline.
    """

    stage: str
    status: str
    detail: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_payload(self) -> Dict[str, Any]:
        payload = {
            "stage": self.stage,
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.detail is not None:
            payload["detail"] = self.detail
        return payload


class WorkflowTracer:
    """
    Collects workflow events to feed frontend visualizations and logs.
    """

    def __init__(self) -> None:
        self._global_events: List[WorkflowEvent] = []
        self._agent_events: Dict[str, List[WorkflowEvent]] = defaultdict(list)

    @property
    def events(self) -> List[WorkflowEvent]:
        return list(self._global_events)

    def emit(
        self,
        stage: str,
        status: str,
        detail: Optional[str] = None,
        *,
        mission_id: Optional[str] = None,
        elf_id: Optional[str] = None,
    ) -> WorkflowEvent:
        event = WorkflowEvent(stage=stage, status=status, detail=detail)
        resolved_key: Optional[str] = None
        if mission_id:
            resolved_key = mission_id
        elif elf_id:
            resolved_key = elf_id
        elif "." in stage:
            resolved_key = stage.split(".", 1)[0]

        if resolved_key:
            key = resolved_key
            self._agent_events[key].append(event)
        else:
            self._global_events.append(event)
        return event

    def serialize(self) -> List[Dict[str, Any]]:
        return [event.to_payload() for event in self._global_events]

    def agent_timeline(self, *, mission_id: Optional[str] = None, elf_id: Optional[str] = None) -> List[Dict[str, Any]]:
        events: List[WorkflowEvent] = []
        if mission_id and mission_id in self._agent_events:
            events.extend(self._agent_events[mission_id])
        if elf_id and elf_id in self._agent_events:
            events.extend(self._agent_events[elf_id])
        allowed_stages = {"mission.created", "mission.dispatched", "agent.completed"}
        filtered = [event for event in events if event.stage in allowed_stages]
        filtered.sort(key=lambda event: event.timestamp)
        return [event.to_payload() for event in filtered]
