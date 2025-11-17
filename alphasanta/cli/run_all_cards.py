"""Launch MicroElf, MoodElf, MacroElf, and Santa AgentCards together."""

from __future__ import annotations

import argparse
import asyncio

from alphasanta.agentcard import (
    CardConfig,
    ElfAgentExecutor,
    SantaAgentExecutor,
    parse_context_as_user_letter,
)
from alphasanta.app import AlphaSantaApplication
from .utils import serve_agentcard


async def main_async(host: str, base_port: int) -> None:
    app = AlphaSantaApplication()

    async def micro_handler(letter):
        return await app.micro_runner.run(letter)

    async def mood_handler(letter):
        return await app.mood_runner.run(letter)

    async def macro_handler(letter):
        return await app.macro_runner.run(letter)

    async def santa_handler(letter):
        return await app.santa_agent.process_letter(letter)

    tasks = [
        serve_agentcard(
            CardConfig(
                name="MicroElf",
                description="Technical analysis elf leveraging CryptoPowerData.",
                host=host,
                port=base_port,
                skill_id="micro_elf",
                skill_name="Micro Technical Analysis",
                skill_description="Provides technical analysis using crypto power data indicators.",
            ),
            ElfAgentExecutor(handler=micro_handler, parser=parse_context_as_user_letter),
        ),
        serve_agentcard(
            CardConfig(
                name="MoodElf",
                description="Sentiment analyst fetching fresh narratives via Tavily.",
                host=host,
                port=base_port + 1,
                skill_id="mood_elf",
                skill_name="Market Sentiment Check",
                skill_description="Collects web narratives and summarizes mood around a token.",
            ),
            ElfAgentExecutor(handler=mood_handler, parser=parse_context_as_user_letter),
        ),
        serve_agentcard(
            CardConfig(
                name="MacroElf",
                description="Macro strategist combining long-horizon indicators and macro news.",
                host=host,
                port=base_port + 2,
                skill_id="macro_elf",
                skill_name="Macro & Liquidity Analysis",
                skill_description="Assesses macroeconomic forces impacting the token.",
            ),
            ElfAgentExecutor(handler=macro_handler, parser=parse_context_as_user_letter),
        ),
        serve_agentcard(
            CardConfig(
                name="Santa",
                description="Final decision-maker orchestrating the AlphaSanta council.",
                host=host,
                port=base_port + 10,
                skill_id="santa",
                skill_name="Santa Council Verdict",
                skill_description="Aggregates elf reports and issues the final verdict.",
            ),
            SantaAgentExecutor(handler=santa_handler, parser=parse_context_as_user_letter),
        ),
    ]
    await asyncio.gather(*tasks)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all AlphaSanta AgentCard services together.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=13000, help="Base port for MicroElf. Mood=+1, Macro=+2, Santa=+10.")
    args = parser.parse_args()

    asyncio.run(
        main_async(
            host=args.host,
            base_port=args.port,
        )
    )


if __name__ == "__main__":
    main()
