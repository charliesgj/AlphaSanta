"""Async queue for sequencing Santa decisions."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Optional

from alphasanta.schema import UserLetter, SantaDecision

logger = logging.getLogger(__name__)


@dataclass
class SantaTask:
    """Represents one pending decision for Santa."""

    letter: UserLetter
    metadata: dict = field(default_factory=dict)

    @property
    def source(self) -> str:
        return self.letter.source


Callback = Callable[[SantaTask, SantaDecision], Awaitable[None]]


class SantaQueue:
    """Asynchronous FIFO queue that feeds tasks to a SantaAgent."""

    def __init__(
        self,
        *,
        santa_agent,
        maxsize: int = 0,
        result_callback: Optional[Callback] = None,
        health_monitor=None,
        rate_limiter=None,
        rate_key=lambda task: task.source,
    ):
        self._queue: asyncio.Queue[SantaTask] = asyncio.Queue(maxsize=maxsize)
        self._santa = santa_agent
        self._result_callback = result_callback
        self._health_monitor = health_monitor
        self._rate_limiter = rate_limiter
        self._rate_key = rate_key
        self._worker_task: Optional[asyncio.Task[None]] = None
        self._stop_event = asyncio.Event()

    async def enqueue_letter(
        self,
        letter: UserLetter,
        *,
        metadata: Optional[dict] = None,
    ) -> None:
        await self._enqueue(
            SantaTask(
                letter=letter,
                metadata=metadata or {},
            )
        )

    async def _enqueue(self, task: SantaTask) -> None:
        if self._rate_limiter and not self._rate_limiter.allow(self._rate_key(task)):
            raise RuntimeError("Rate limit exceeded for task source")
        await self._queue.put(task)
        logger.info("Enqueued Santa task source=%s", task.source)

    async def start(self) -> None:
        if self._worker_task and not self._worker_task.done():
            return
        self._stop_event.clear()
        self._worker_task = asyncio.create_task(self._worker_loop())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

    async def _worker_loop(self) -> None:
        logger.info("SantaQueue worker started")
        try:
            while not self._stop_event.is_set():
                task = await self._queue.get()
                try:
                    decision = await self._santa.process_letter(task.letter)

                    if self._health_monitor:
                        self._health_monitor.record_success()
                    if self._result_callback:
                        await self._result_callback(task, decision)
                except Exception as exc:  # pragma: no cover - defensive
                    logger.exception("Santa decision failed: %s", exc)
                    if self._health_monitor:
                        self._health_monitor.record_failure(exc)
                finally:
                    self._queue.task_done()
        except asyncio.CancelledError:
            logger.info("SantaQueue worker cancelled")
            raise

    async def join(self) -> None:
        """Wait for all queued tasks to complete."""
        await self._queue.join()
