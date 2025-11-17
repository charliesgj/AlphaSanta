"""
AlphaElf – autonomous alpha discovery agent.
"""

from __future__ import annotations

from typing import Iterable, Optional, ClassVar

from spoon_ai.tools.base import BaseTool

from .base import ElfAgent
from ..schema import UserLetter, ElfReport


class AlphaElf(ElfAgent):
    """
    AlphaElf consumes algorithmic alpha signals and emits an ElfReport directly.

    Unlike other elves, it does not require community input and can operate
    autonomously to keep the pipeline active during idle periods.
    """

    elf_id: ClassVar[str] = "alpha"
    name: ClassVar[str] = "AlphaElf"
    description: ClassVar[str] = "Autonomous scout that surfaces promising alpha opportunities."
    system_prompt: ClassVar[str] = (
        "You are AlphaElf. You combine proprietary quantitative signals with "
        "market intuition to surface actionable alpha ideas. When provided a "
        "signal payload, explain why it matters, cite key metrics, and yield "
        "a confidence score between 0 and 1."
    )

    def __init__(self, *, tools: Optional[Iterable[BaseTool]] = None):
        super().__init__(tools=tools)

    def build_tools(self) -> Iterable[BaseTool]:
        # AlphaElf relies on upstream algorithmic inputs, no tools by default.
        return []

    async def from_signal(self, token: str, thesis: str, signal_payload: str) -> ElfReport:
        """
        Use a precomputed signal payload as thesis context and run the standard analysis.
        """
        combined_thesis = thesis or "Algorithmic alpha candidate."
        enriched_thesis = f"{combined_thesis}\nSignal Details:\n{signal_payload}"
        letter = UserLetter(token=token, thesis=enriched_thesis, source="alpha-elf")
        return await self.analyze_input(letter)
