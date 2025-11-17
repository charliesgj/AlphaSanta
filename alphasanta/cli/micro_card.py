"""Launch MicroElf as an AgentCard service."""

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
    parser = argparse.ArgumentParser(description="Run MicroElf AgentCard server.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=12001)
    args = parser.parse_args()

    async def handler(letter):
        return await get_app().micro_runner.run(letter)

    executor = ElfAgentExecutor(handler=handler, parser=parse_context_as_user_letter)
    config = CardConfig(
        name="MicroElf",
        description="Technical analysis elf leveraging CryptoPowerData.",
        host=args.host,
        port=args.port,
        skill_id="micro_elf",
        skill_name="Micro Technical Analysis",
        skill_description="Provides technical analysis using crypto power data indicators.",
        tags=["technical", "crypto"],
    )
    run_agentcard(config, executor)


if __name__ == "__main__":
    main()
