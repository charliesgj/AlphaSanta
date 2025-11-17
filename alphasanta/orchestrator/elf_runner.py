"""Thread-safe wrappers around Elf agents."""

from __future__ import annotations

import asyncio
from typing import Callable, Any, Optional
from ..schema import UserLetter, ElfReport


class ElfRunner:
    def __init__(self, agent_factory: Callable[[], Any]) -> None:
        self._agent = agent_factory()
        self._lock: Optional[asyncio.Lock] = None

    def _ensure_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def run(self, letter: UserLetter) -> ElfReport:
        async with self._ensure_lock():
            try:
                return await self._agent.analyze_input(letter)
            finally:
                self._agent.clear()
