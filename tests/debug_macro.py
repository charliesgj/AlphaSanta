import asyncio

from alphasanta.agents.macro import MacroElf
from alphasanta.schema import UserLetter


async def main():
    elf = MacroElf()
    letter = UserLetter(token="BTC", thesis="ETF demand surge")
    report = await elf.analyze_input(letter)
    print("analysis", report.analysis[:500])


if __name__ == "__main__":
    asyncio.run(main())
