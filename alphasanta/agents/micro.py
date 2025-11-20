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
            f"Judge if the following thesis is plausible by running following steps: {letter.thesis}\n"
            "1. Pull last 7 day OHLCV data of given token using crypto_powerdata_cex.\n"
            "2. Summarize technical signals for data pulled in last step.\n"
            "only include (MACD,RSI, MA/EMA, Bolling Bards). Do not use over 3 signals. Pick randomly from the given 5\n"
            "3. Summarize key data indicators and give your opinion on the token and letter and a score for the letter's plausiblity, strictly follow the given format.\n"
            "4. Organize your output to be complete, smooth, rational, while humanlike, within 200 words."
            f"Format: {self.elf_id}'s evaluation of this letter:\n"
            "Confidence Score: <float>\n"
        )

    def post_process(self, assistant_response: str) -> ElfReport:
        # Basic parsing for the confidence line
        confidence = None
        for raw_line in assistant_response.splitlines():
            line = raw_line.strip(" *-_\t")
            if not line:
                continue
            lower = line.lower()
            if lower.startswith("confidence"):
                try:
                    confidence = float(line.split(":", 1)[1].strip())
                    break
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
