"""
AlphaSanta package root.

Provides shared types and helpers for orchestrating the Santa/Elf multi-agent
workflow on top of Spoon Core.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

from dotenv import load_dotenv

__all__ = ["__version__", "AlphaSantaApplication"]

__version__ = "0.1.0"

load_dotenv()


def __getattr__(name: str) -> Any:  # pragma: no cover
    if name == "AlphaSantaApplication":
        return import_module("alphasanta.app").AlphaSantaApplication
    raise AttributeError(name)
