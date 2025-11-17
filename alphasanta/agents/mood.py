"""
MoodElf – market sentiment specialist using Tavily MCP.
"""

from __future__ import annotations

import os
from typing import Iterable, ClassVar

from spoon_ai.tools.mcp_tool import MCPTool

from .base import ElfAgent
from ..schema import UserLetter, ElfReport


class MoodElf(ElfAgent):
    elf_id: ClassVar[str] = "mood"
    name: ClassVar[str] = "MoodElf"
    description: ClassVar[str] = "Sentiment scout aggregating narratives, social buzz, and news."
    system_prompt: ClassVar[str] = (
        "You are MoodElf, the sentiment specialist of AlphaSanta.\n"
        "Use tavily-search to gather fresh articles, social posts, and narratives.\n"
        "Summarize the overall market mood, highlight catalysts or risks, "
        "and provide a confidence score between 0 and 1."
    )

    def build_tools(self) -> Iterable[MCPTool]:
        tavily_key = os.getenv("TAVILY_API_KEY", "")
        if not tavily_key:
            raise RuntimeError("MoodElf requires TAVILY_API_KEY in the environment.")

        return [
            MCPTool(
                name="tavily-search",
                description="Multi-source search tool for real-time news and sentiment.",
                mcp_config={
                    "command": "npx",
                    "args": ["--yes", "tavily-mcp"],
                    "env": {"TAVILY_API_KEY": tavily_key},
                    "transport": "stdio",
                },
            )
        ]

    def render_user_prompt(self, letter: UserLetter) -> str:
        return (
            "You are MoodElf assessing sentiment.\n"
            f"Token: {letter.token}\n"
            f"Community thesis: {letter.thesis}\n"
            "Steps:\n"
            "1. Use tavily-search with queries around the token, ticker, and sector.\n"
            "2. Cluster findings into positive / neutral / negative narratives.\n"
            "3. Highlight influential voices, catalysts, or FUD.\n"
            "4. Output a confidence score between 0 and 1.\n"
            "Format:\n"
            "Narrative Summary:\n"
            "- ...\n"
            "Key Sources:\n"
            "- ...\n"
            "Confidence: <float>\n"
        )

    def post_process(self, assistant_response: str) -> ElfReport:
        confidence = None
        for line in assistant_response.splitlines():
            if line.lower().startswith("confidence"):
                try:
                    confidence = float(line.split(":")[1].strip())
                except Exception:
                    confidence = None
        return ElfReport(
            elf_id=self.elf_id,
            analysis=assistant_response,
            confidence=confidence,
            meta={
                "token": self._context.token if self._context else None,
                "thesis": self._context.thesis if self._context else None,
            },
        )
