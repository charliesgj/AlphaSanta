"""
MicroElf – technical analysis specialist.
"""

from __future__ import annotations

from typing import Iterable, ClassVar

from spoon_toolkits.crypto.crypto_powerdata.tools import CryptoPowerDataCEXTool

from .base import ElfAgent
from ..schema import UserLetter, ElfReport


class MicroElf(ElfAgent):
    elf_id: ClassVar[str] = "micro"
    name: ClassVar[str] = "MicroElf"
    description: ClassVar[str] = "Technical analysis elf focusing on price action and indicators."
    system_prompt: ClassVar[str] = (
        "You are MicroElf, the technical analyst of AlphaSanta.\n"
        "You are an expert in chart patterns, technical indicators, and price action.\n"
        "You obsess over price/volume generated signals. And make bold discretion on the future trend of the crypto.\n"
        "Always reference indicator evidence when forming an opinion.\n"
        "Provide a confidence score between 0 and 1."
    )

    def build_tools(self) -> Iterable[CryptoPowerDataCEXTool]:
        return [
            CryptoPowerDataCEXTool(
                name="crypto_powerdata_cex",
                description="Fetches OHLCV plus indicators for spot pairs.",
            )
        ]

    def configure_tools(self, letter: UserLetter) -> None:
        tool = self.avaliable_tools.get_tool("crypto_powerdata_cex")
        symbol = self._normalize_symbol(letter.token)
        tool.exchange = "binance"
        tool.symbol = symbol
        tool.timeframe = "1h"
        tool.limit = 72

    def render_user_prompt(self, letter: UserLetter) -> str:
        return (
            f"You are MicroElf evaluating {letter.token}.\n"
            f"Community thesis: {letter.thesis}\n"
            "1. Pull recent OHLCV data using crypto_powerdata_cex.\n"
            "2. Summarize key technical signals (MACD,RSI,momentum_indicator, support/resistance). Do not use over 5 signals.\n"
            "3. Provide a recommendation (bullish/bearish/neutral) with confidence [0-1].\n"
            "Format:\n"
            "Analysis:\n"
            "- ...\n"
            "Confidence: <float>\n"
        )

    def post_process(self, assistant_response: str) -> ElfReport:
        # Basic parsing for the confidence line
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
                "timeframe": "1h",
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
