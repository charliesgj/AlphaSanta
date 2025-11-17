"""Launch SantaAgent as an AgentCard service."""

from __future__ import annotations

import argparse

from alphasanta.agentcard import (
    CardConfig,
    SantaAgentExecutor,
    parse_context_as_user_letter,
)
from alphasanta.app import AlphaSantaApplication
from .utils import run_agentcard

_app: AlphaSantaApplication | None = None


def get_app() -> AlphaSantaApplication:
    global _app
    if _app is None:
        _app = AlphaSantaApplication()
    return _app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Santa AgentCard server.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=12010)
    args = parser.parse_args()

    async def handler(letter):
        app = get_app()
        return await app.santa_agent.process_letter(letter)

    executor = SantaAgentExecutor(handler=handler, parser=parse_context_as_user_letter)
    config = CardConfig(
        name="Santa",
        description="Final decision-maker orchestrating the AlphaSanta council.",
        host=args.host,
        port=args.port,
        skill_id="santa",
        skill_name="Santa Council Verdict",
        skill_description="Aggregates elf reports and issues the final verdict.",
        tags=["orchestration", "santa"],
    )
    run_agentcard(config, executor)


if __name__ == "__main__":
    main()
