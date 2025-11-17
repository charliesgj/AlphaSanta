"""
Factory helpers for exposing AlphaSanta agents via AgentCard.
"""

from __future__ import annotations

import inspect
import json
import logging
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, Optional

from alphasanta.schema import UserLetter, ElfReport, SantaDecision

try:
    from a2a.server.agent_execution import AgentExecutor
    from a2a.server.agent_execution.context import RequestContext
    from a2a.server.apps import A2AStarletteApplication
    from a2a.server.events.event_queue import EventQueue
    from a2a.server.request_handlers import DefaultRequestHandler
    from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
    from a2a.types import AgentCapabilities, AgentCard, AgentSkill, Part, TextPart
except ImportError as exc:  # pragma: no cover - optional dependency
    raise RuntimeError(
        "google-a2a SDK not installed. Install with `pip install '.[agentcard]'`."
    ) from exc

logger = logging.getLogger(__name__)

ParseFn = Callable[[RequestContext], UserLetter]
ElfHandler = Callable[[UserLetter], Awaitable[ElfReport]]
SantaHandler = Callable[[UserLetter], Awaitable[SantaDecision]]


@dataclass
class CardConfig:
    name: str
    description: str
    host: str = "localhost"
    port: int = 10000
    skill_id: str = "alpha_analysis"
    skill_name: str = "Alpha Analysis"
    skill_description: str = "Evaluate community-submitted alpha."
    tags: Optional[list[str]] = None
    examples: Optional[list[str]] = None
    version: str = "0.1.0"

    def to_agent_card(self) -> AgentCard:
        capabilities = AgentCapabilities(streaming=False)
        skill = AgentSkill(
            id=self.skill_id,
            name=self.skill_name,
            description=self.skill_description,
            tags=self.tags or ["crypto", "analysis"],
            examples=self.examples or ["{\"token\": \"BTC\", \"thesis\": \"New ETF demand.\"}"],
        )
        return AgentCard(
            name=self.name,
            description=self.description,
            url=f"http://{self.host}:{self.port}/",
            version=self.version,
            defaultInputModes=["text/plain", "application/json"],
            defaultOutputModes=["application/json"],
            capabilities=capabilities,
            skills=[skill],
        )


class ElfAgentExecutor(AgentExecutor):
    """Minimal executor that runs a coroutine returning ElfReport."""

    def __init__(self, handler: ElfHandler, parser: ParseFn):
        self.handler = handler
        self.parser = parser

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        if not context.message:
            raise ValueError("RequestContext.message is required")
        if not context.task_id or not context.context_id:
            raise ValueError("Task metadata missing")

        letter = self.parser(context)
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        if not context.current_task:
            updater.submit()
        updater.start_work()

        report = await self.handler(letter)
        parts = [Part(root=TextPart(text=json.dumps(report.to_agentcard_payload(), ensure_ascii=False)))]

        await _maybe_await(updater.add_artifact(parts))
        await _maybe_await(updater.complete())

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await _maybe_await(updater.fail("Cancellation requested."))


class SantaAgentExecutor(AgentExecutor):
    """Executor wrapping Santa decision making."""

    def __init__(self, handler: SantaHandler, parser: ParseFn):
        self.handler = handler
        self.parser = parser

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        if not context.message:
            raise ValueError("RequestContext.message is required")
        if not context.task_id or not context.context_id:
            raise ValueError("Task metadata missing")

        letter = self.parser(context)
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        if not context.current_task:
            updater.submit()
        updater.start_work()

        decision = await self.handler(letter)
        parts = [Part(root=TextPart(text=json.dumps(decision.to_dict(), ensure_ascii=False)))]

        await _maybe_await(updater.add_artifact(parts))
        await _maybe_await(updater.complete())

    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await _maybe_await(updater.fail("Cancellation requested."))


def build_agentcard_server(
    *,
    config: CardConfig,
    executor: AgentExecutor,
) -> A2AStarletteApplication:
    """
    Construct an A2AStarletteApplication ready to be served with uvicorn.
    """
    agent_card = config.to_agent_card()
    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
    )
    return A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )


def parse_context_as_user_letter(context: RequestContext) -> UserLetter:
    """
    Parse the incoming RequestContext message as JSON -> UserLetter.
    """
    if not context.message:
        raise ValueError("Missing message payload")

    text_chunks = []
    for part in context.message.parts:
        root = part.root
        if isinstance(root, TextPart):
            text_chunks.append(root.text)

    if not text_chunks:
        raise ValueError("Expected text/plain payload with token/thesis JSON.")

    try:
        payload = json.loads("\n".join(text_chunks))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON payload: {exc}") from exc

    token = payload.get("token")
    thesis = payload.get("thesis")
    if not token or not thesis:
        raise ValueError("Payload must include 'token' and 'thesis'.")

    source = payload.get("source", "community")
    return UserLetter(token=token, thesis=thesis, source=source)


async def _maybe_await(result):
    if inspect.isawaitable(result):
        return await result
    return result
