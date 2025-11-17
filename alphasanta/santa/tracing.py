"""
Workflow tracing utilities for visualizing Santa's decision process.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class WorkflowEvent:
    """
    Represents a single step in the Santa workflow timeline.
    """

    stage: str
    status: str
    detail: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.utcnow())

    def to_payload(self) -> Dict[str, Any]:
        return {
            "stage": self.stage,
            "status": self.status,
            "detail": self.detail,
            "timestamp": self.timestamp.isoformat(),
        }


class WorkflowTracer:
    """
    Collects workflow events to feed frontend visualizations and logs.
    """

    def __init__(self) -> None:
        self._events: List[WorkflowEvent] = []

    @property
    def events(self) -> List[WorkflowEvent]:
        return list(self._events)

    def emit(self, stage: str, status: str, detail: Optional[str] = None) -> WorkflowEvent:
        event = WorkflowEvent(stage=stage, status=status, detail=detail)
        self._events.append(event)
        return event

    def serialize(self) -> List[Dict[str, Any]]:
        return [event.to_payload() for event in self._events]
