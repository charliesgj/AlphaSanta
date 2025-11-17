"""
SantaCoordinator orchestrates elf analyses and aggregates their reports.
"""

from __future__ import annotations

import asyncio
from typing import Iterable, List, Sequence

from ..orchestrator.elf_runner import ElfRunner
from ..schema import UserLetter, CouncilResult, ElfReport


class SantaCoordinator:
    """
    Runs all elves in parallel and synthesizes a combined verdict.
    """

    def __init__(self, *, runners: Sequence[ElfRunner]) -> None:
        self.runners = list(runners)

    async def gather_reports(self, letter: UserLetter) -> List[ElfReport]:
        tasks = [runner.run(letter) for runner in self.runners]
        return await asyncio.gather(*tasks)

    async def evaluate(self, letter: UserLetter) -> CouncilResult:
        reports = await self.gather_reports(letter)
        summary = self.summarize_reports(reports)
        return CouncilResult(user_letter=letter, reports=reports, summary=summary)

    @staticmethod
    def summarize_reports(reports: Sequence[ElfReport]) -> str:
        lines = [report.brief() for report in reports]
        return "\n".join(lines)
