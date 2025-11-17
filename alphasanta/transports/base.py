"""
Interfaces for elf transport layers (local runners, A2A clients, etc.).
"""

from __future__ import annotations

from typing import Protocol, Sequence

from ..schema import UserLetter, ElfReport
from ..santa.tracing import WorkflowTracer


class ElfTransport(Protocol):
    """
    Abstraction for invoking elves. Concrete transports may call local runners
    or remote AgentCard services (A2A).
    """

    @property
    def elf_ids(self) -> Sequence[str]:
        ...

    async def fetch_report(self, elf_id: str, letter: UserLetter, tracer: WorkflowTracer) -> ElfReport:
        ...
