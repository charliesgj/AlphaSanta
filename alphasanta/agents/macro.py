"""
MacroElf – macro & fundamental narrative analyst.
"""

from __future__ import annotations

import os
from typing import Iterable, ClassVar

from spoon_toolkits.crypto.crypto_powerdata.tools import CryptoPowerDataIndicatorsTool, CryptoPowerDataCEXTool

try:
    from spoon_toolkits.data_platforms.desearch.builtin_tools import DesearchAISearchTool
except ImportError:  # Desearch optional
    DesearchAISearchTool = None  # type: ignore

from .base import ElfAgent
from ..schema import UserLetter, ElfReport


class MacroElf(ElfAgent):
    elf_id: ClassVar[str] = "macro"
    name: ClassVar[str] = "MacroElf"
    description: ClassVar[str] = "Macro strategist tracking regulatory, liquidity, and capital flows."
    system_prompt: ClassVar[str] = (
        "You are MacroElf, the macroeconomic analyst of AlphaSanta.\n"
        "You are good at connecting macro trends to crypto market impacts.\n"
        "You collect news and data to form a big-picture view.\n"
        "You know about the big picture of the market by learning how BTC/ETH/SOL behave under different macro regimes.\n"
        "Combine long-horizon indicators with macro policy and liquidity themes.\n"
        "Discuss how global events could impact the token and provide confidence [0-1]."
    )

    def build_tools(self) -> Iterable:
        tools: list = [
            CryptoPowerDataCEXTool(
                name="crypto_powerdata_cex",
                description="Daily technical + volume context for macro framing.",
            ),
            CryptoPowerDataIndicatorsTool(
                name="crypto_powerdata_indicators",
                description="Long-horizon indicator snapshots for technical context.",
            )
        ]
        if DesearchAISearchTool and os.getenv("DESEARCH_API_KEY"):
            tools.append(
                DesearchAISearchTool(
                    name="desearch_ai_search",
                    description="Aggregates macro news and research across the web.",
                )
            )
        return tools

    def configure_tools(self, letter: UserLetter) -> None:
        cex_tool = self.avaliable_tools.get_tool("crypto_powerdata_cex")
        cex_tool.exchange = "binance"
        cex_tool.symbol = self._normalize_symbol(letter.token)
        cex_tool.timeframe = "3d"
        cex_tool.limit = 60

    def render_user_prompt(self, letter: UserLetter) -> str:
        sources = ["crypto_powerdata_cex", "crypto_powerdata_indicators"]
        if self.avaliable_tools.tool_map.get("desearch_ai_search"):
            sources.append("desearch_ai_search")

        return (
            "You are MacroElf.\n"
            f"Token: {letter.token}\n"
            f"Community thesis: {letter.thesis}\n"
            f"Tools available: {', '.join(sources)}\n"
            "1. Use long-term indicators to assess trend, volatility, and regime shifts.\n"
            "2. Research macro catalysts (rates, liquidity, regulation, sector rotations).\n"
            "3. Summarize tailwinds/headwinds.\n"
            "4. Output confidence [0,1].\n"
            "Format:\n"
            "Macro View:\n"
            "- ...\n"
            "Drivers:\n"
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
                "timeframe": "1d",
                "uses_desearch": bool(self.avaliable_tools.tool_map.get("desearch_ai_search")),
            },
        )

    @staticmethod
    def _normalize_symbol(token: str) -> str:
        token = token.strip().upper()
        if "/" in token:
            return token
        if token.endswith("USDT"):
            return token[:-4] + "/USDT"
        if token.endswith("USD"):
            return token[:-3] + "/USD"
        return f"{token}/USDT"
