"""Santa orchestration utilities."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["SantaAgent", "WorkflowTracer"]


def __getattr__(name: str) -> Any:  # pragma: no cover - thin wrapper
    if name == "SantaAgent":
        from .agent import SantaAgent

        return SantaAgent
    if name == "WorkflowTracer":
        from .tracing import WorkflowTracer

        return WorkflowTracer
    raise AttributeError(name)
