"""Santa orchestration utilities."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["SantaAgent", "SantaCoordinator", "parse_santa_response", "WorkflowTracer"]


def __getattr__(name: str) -> Any:  # pragma: no cover - thin wrapper
    if name == "SantaAgent":
        from .agent import SantaAgent

        return SantaAgent
    if name == "SantaCoordinator":
        from .coordinator import SantaCoordinator

        return SantaCoordinator
    if name == "parse_santa_response":
        from .utils import parse_santa_response

        return parse_santa_response
    if name == "WorkflowTracer":
        from .tracing import WorkflowTracer

        return WorkflowTracer
    raise AttributeError(name)
