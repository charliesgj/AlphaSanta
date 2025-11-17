"""Launch MoodElf as an AgentCard service."""

from __future__ import annotations

import argparse

from alphasanta.agentcard import CardConfig, ElfAgentExecutor, parse_context_as_user_letter
from alphasanta.app import AlphaSantaApplication
from .utils import run_agentcard

_app: AlphaSantaApplication | None = None


def get_app() -> AlphaSantaApplication:
    global _app
    if _app is None:
        _app = AlphaSantaApplication()
    return _app


def main() -> None:
    parser = argparse.ArgumentParser(description="Run MoodElf AgentCard server.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=12002)
    args = parser.parse_args()

    async def handler(letter):
        return await get_app().mood_runner.run(letter)

    executor = ElfAgentExecutor(handler=handler, parser=parse_context_as_user_letter)
    config = CardConfig(
        name="MoodElf",
        description="Sentiment analyst fetching fresh narratives via Tavily.",
        host=args.host,
        port=args.port,
        skill_id="mood_elf",
        skill_name="Market Sentiment Check",
        skill_description="Collects web narratives and summarizes mood around a token.",
        tags=["sentiment", "news"],
    )
    run_agentcard(config, executor)


if __name__ == "__main__":
    main()
