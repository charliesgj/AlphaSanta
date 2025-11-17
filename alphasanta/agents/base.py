"""
Base class for AlphaSanta elves.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List, Optional, ClassVar

from spoon_ai.agents.toolcall import ToolCallAgent
from spoon_ai.chat import ChatBot
from spoon_ai.tools import ToolManager
from spoon_ai.tools.base import BaseTool

from ..schema import UserLetter, ElfReport


class ElfAgent(ToolCallAgent, ABC):
    """
    Shared behavior for elf agents.

    Subclasses should provide:
        - `elf_id`: stable identifier used by Santa and AgentCard
        - `system_prompt`: persona/role instructions
        - `build_tools()`: list of BaseTool or MCPTool instances
        - `pre_prompt(token, thesis)`: user message string (optional)
        - `post_process(response)` to produce ElfReport
    """

    elf_id: ClassVar[str] = "elf"
    llm_provider: ClassVar[str] = "anthropic"
    llm_model: ClassVar[str] = "claude-haiku-4-5-20251001"

    def __init__(
        self,
        *,
        llm: Optional[ChatBot] = None,
        tools: Optional[Iterable[BaseTool]] = None,
        max_steps: int = 5,
    ) -> None:
        self._context: Optional[UserLetter] = None

        avaliable_tools = ToolManager(list(tools) if tools else list(self.build_tools()))

        super().__init__(
            llm=llm or ChatBot(llm_provider=self.llm_provider, model_name=self.llm_model),
            avaliable_tools=avaliable_tools,
            max_steps=max_steps,
        )

    # Lifecycle -----------------------------------------------------------------

    def prepare(self, letter: UserLetter) -> None:
        """Cache token context and give subclasses a chance to adjust tool inputs."""
        self._context = letter
        self.configure_tools(letter)

    async def analyze(self, token: str, thesis: str) -> ElfReport:
        """
        Execute the elf's reasoning loop and return a structured report.
        """
        letter = UserLetter(token=token, thesis=thesis)
        return await self.analyze_input(letter)

    async def analyze_input(self, letter: UserLetter) -> ElfReport:
        self.prepare(letter)
        user_prompt = self.render_user_prompt(letter)

        response_text = await self.run(user_prompt)
        return self.post_process(response_text)

    # Hooks ---------------------------------------------------------------------

    @abstractmethod
    def build_tools(self) -> Iterable[BaseTool]:
        """Instantiate tool instances specific to the elf."""

    def configure_tools(self, letter: UserLetter) -> None:
        """
        Optional hook for subclasses to update tool parameters before each run.

        Default implementation is a no-op.
        """

    def render_user_prompt(self, letter: UserLetter) -> str:
        """
        Build the user-facing prompt fed to the agent.
        """
        return (
            f"Token: {letter.token}\n"
            f"Community thesis: {letter.thesis}\n"
            "Evaluate the thesis from your perspective. "
            "Use tools when helpful, cite key evidence, and provide a confidence score."
        )

    def post_process(self, assistant_response: str) -> ElfReport:
        """
        Convert raw assistant text into an ElfReport.

        Subclasses should override to parse structured outputs or extract
        confidence. Default implementation wraps the string response.
        """
        token = self._context.token if self._context else None
        thesis = self._context.thesis if self._context else None
        return ElfReport(
            elf_id=self.elf_id,
            analysis=assistant_response,
            meta={
                "token": token,
                "thesis": thesis,
            },
        )

    # Utility -------------------------------------------------------------------

    async def stream_analysis(self, token: str, thesis: str) -> ElfReport:
        """
        Convenience wrapper to run analyze() ensuring cleanup.
        """
        try:
            letter = UserLetter(token=token, thesis=thesis)
            return await self.analyze_input(letter)
        finally:
            await self._cleanup()

    async def _cleanup(self) -> None:
        """Clear memory between runs to avoid cross-contamination."""
        self.clear()
        await asyncio.sleep(0)  # yield control
