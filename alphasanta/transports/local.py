"""
Local in-process transport that keeps using ElfRunner instances.

This is useful for tests and development before wiring A2A transport.
"""

from __future__ import annotations

from typing import Dict, Mapping, Sequence

from ..orchestrator.elf_runner import ElfRunner
from ..schema import UserLetter, ElfReport
from ..santa.tracing import WorkflowTracer
from .base import ElfTransport


class LocalElfTransport(ElfTransport):
    """
    Executes elves via their local ElfRunner counterparts.
    """

    def __init__(self, runners: Mapping[str, ElfRunner]) -> None:
        self._runners: Dict[str, ElfRunner] = dict(runners)

    @property
    def elf_ids(self) -> Sequence[str]:
        return tuple(self._runners.keys())

    async def fetch_report(self, elf_id: str, letter: UserLetter, tracer: WorkflowTracer) -> ElfReport:
        runner = self._runners.get(elf_id)
        if runner is None:
            raise ValueError(f"No runner registered for elf_id={elf_id}")

        tracer.emit(f"{elf_id}.dispatch", "start", detail=f"token={letter.token}")
        report = await runner.run(letter)
        tracer.emit(
            f"{elf_id}.dispatch",
            "success",
            detail=f"confidence={report.confidence}" if report.confidence is not None else None,
        )
        return report
