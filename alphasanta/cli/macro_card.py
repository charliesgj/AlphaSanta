"""Launch MacroElf as an AgentCard service."""

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
    parser = argparse.ArgumentParser(description="Run MacroElf AgentCard server.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=12003)
    args = parser.parse_args()

    async def handler(letter):
        return await get_app().macro_runner.run(letter)

    executor = ElfAgentExecutor(handler=handler, parser=parse_context_as_user_letter)
    config = CardConfig(
        name="MacroElf",
        description="Macro strategist combining long-horizon indicators and macro news.",
        host=args.host,
        port=args.port,
        skill_id="macro_elf",
        skill_name="Macro & Liquidity Analysis",
        skill_description="Assesses macroeconomic forces impacting the token.",
        tags=["macro", "liquidity"],
    )
    run_agentcard(config, executor)


if __name__ == "__main__":
    main()
