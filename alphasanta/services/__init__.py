"""Service layer exports."""

from __future__ import annotations

from typing import Any

__all__ = [
    "DisseminationService",
    "PersistenceService",
    "SubmissionWorker",
]


def __getattr__(name: str) -> Any:  # pragma: no cover
    if name == "DisseminationService":
        from .dissemination import DisseminationService

        return DisseminationService
    if name == "PersistenceService":
        from .persistence import PersistenceService

        return PersistenceService
    if name == "SubmissionWorker":
        from .submission_worker import SubmissionWorker

        return SubmissionWorker
    raise AttributeError(name)
