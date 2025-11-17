"""AlphaSanta application context for shared resources."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from ..agents import AlphaElf, MacroElf, MicroElf, MoodElf
from spoon_ai.chat import ChatBot
from ..config import get_settings
from ..orchestrator.elf_runner import ElfRunner
from ..orchestrator.queue import SantaQueue
from ..infra.monitoring import HealthMonitor, RateLimiter
from ..santa import SantaAgent
from ..schema import UserLetter
from ..services import DisseminationService, PersistenceService, TurnkeyService
from ..transports import LocalElfTransport, A2AElfTransport

logger = logging.getLogger(__name__)


class AlphaSantaApplication:
    def __init__(self) -> None:
        self.settings = get_settings()

        llm_config = lambda: ChatBot(llm_provider=self.settings.llm_provider, model_name=self.settings.llm_model)
        self.micro_runner = ElfRunner(lambda: MicroElf(llm=llm_config()))
        self.mood_runner = ElfRunner(lambda: MoodElf(llm=llm_config()))
        self.macro_runner = ElfRunner(lambda: MacroElf(llm=llm_config()))

        elf_ids = ("micro", "mood", "macro")
        endpoints = {
            "micro": self.settings.a2a_micro_url,
            "mood": self.settings.a2a_mood_url,
            "macro": self.settings.a2a_macro_url,
        }
        transport = None
        if self.settings.elf_transport == "a2a" and all(endpoints.values()):
            try:
                transport = A2AElfTransport(
                    endpoints,
                    timeout=self.settings.a2a_timeout,
                    fallbacks={
                        "micro": self.micro_runner,
                        "mood": self.mood_runner,
                        "macro": self.macro_runner,
                    },
                )
                logger.info("Initialized A2AElfTransport for elves.")
            except Exception as exc:  # pragma: no cover - optional path
                logger.warning("Failed to initialize A2A transport (%s); falling back to local runners.", exc)
                transport = None
        if transport is None:
            transport = LocalElfTransport(
                {
                    "micro": self.micro_runner,
                    "mood": self.mood_runner,
                    "macro": self.macro_runner,
                }
            )
        self.elf_transport = transport
        self.elf_ids = elf_ids

        self.dissemination = DisseminationService(
            neofs_enabled=self.settings.neofs_enabled,
            neofs_container_id=self.settings.neofs_container_id,
            twitter_enabled=self.settings.twitter_enabled,
            telegram_enabled=self.settings.telegram_enabled,
        )
        self.persistence = PersistenceService(self.settings.database_url)
        self.turnkey = TurnkeyService(self.settings) if self.settings.turnkey_enabled() else None

        self.alpha_elf = AlphaElf()
        self.santa_agent = SantaAgent(
            elf_transport=self.elf_transport,
            elf_order=self.elf_ids,
            dissemination=self.dissemination,
            persistence=self.persistence,
            turnkey_service=self.turnkey,
            alpha_elf=self.alpha_elf,
        )

        self.health_monitor = HealthMonitor()
        self.rate_limiter = RateLimiter(self.settings.rate_limit_per_min)

        def _rate_key(task):
            wallet = task.letter.wallet_address
            if wallet:
                return wallet
            return task.source

        self.queue = SantaQueue(
            santa_agent=self.santa_agent,
            maxsize=self.settings.queue_maxsize,
            health_monitor=self.health_monitor,
            rate_limiter=self.rate_limiter,
            rate_key=_rate_key,
        )

        self._queue_started = False

    async def ensure_queue(self) -> None:
        if not self._queue_started:
            await self.queue.start()
            self._queue_started = True

    async def submit_letter(self, letter: UserLetter, *, alpha_signal: Optional[str] = None) -> None:
        await self.ensure_queue()
        await self.queue.enqueue_letter(letter, alpha_signal=alpha_signal)

    async def submit_alpha(self, letter: UserLetter, *, alpha_signal: Optional[str] = None) -> None:
        await self.ensure_queue()
        await self.queue.enqueue_alpha(letter, alpha_signal=alpha_signal)

    async def run_single_letter(self, letter: UserLetter, *, alpha_signal: Optional[str] = None):
        return await self.santa_agent.process_letter(letter, alpha_signal=alpha_signal)

    # Backwards compatibility with earlier API names ---------------------------------

    async def submit_council(self, letter: UserLetter, *, alpha_signal: Optional[str] = None) -> None:
        await self.submit_letter(letter, alpha_signal=alpha_signal)

    async def run_single_council(self, letter: UserLetter, *, alpha_signal: Optional[str] = None):
        return await self.run_single_letter(letter, alpha_signal=alpha_signal)

    async def shutdown(self) -> None:
        if self._queue_started:
            await self.queue.stop()
            self._queue_started = False

    def health(self):
        return self.health_monitor.snapshot()
