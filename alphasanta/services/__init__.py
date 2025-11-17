"""Service layer exports."""

from __future__ import annotations

from typing import Any

__all__ = [
    "DisseminationService",
    "PersistenceService",
    "TurnkeyService",
]


def __getattr__(name: str) -> Any:  # pragma: no cover
    if name == "DisseminationService":
        from .dissemination import DisseminationService

        return DisseminationService
    if name == "PersistenceService":
        from .persistence import PersistenceService

        return PersistenceService
    if name == "TurnkeyService":
        from .turnkey_service import TurnkeyService

        return TurnkeyService
    raise AttributeError(name)
