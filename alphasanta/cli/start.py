"""Launch the full AlphaSanta letter workflow in a single process."""

from __future__ import annotations

import argparse
import asyncio
import json

from alphasanta.app import AlphaSantaApplication
from alphasanta.schema import UserLetter


async def run_workflow(
    *,
    token: str,
    thesis: str,
    user_id: str | None,
) -> None:
    app = AlphaSantaApplication()
    letter = UserLetter(
        token=token,
        thesis=thesis,
        user_id=user_id,
        metadata={},
    )
    decision = await app.run_single_letter(letter)
    elf_responses = decision.meta.get("elf_responses", [])

    print("\n=== Elf Responses ===")
    for response in elf_responses:
        print(json.dumps(response, ensure_ascii=False, indent=2))

    print("\n=== Santa Decision ===")
    print(json.dumps(decision.to_dict(), ensure_ascii=False, indent=2))
    await app.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the AlphaSanta letter-to-decision workflow.")
    parser.add_argument("--token", help="Token symbol (e.g., BTC/USDT).")
    parser.add_argument("--thesis", help="Community thesis or signal description.")
    parser.add_argument("--user-id", help="User identifier (required).")
    args = parser.parse_args()

    token = args.token or input("Token symbol (e.g., BTC/USDT): ").strip()
    thesis = args.thesis or input("Thesis / idea: ").strip()
    user_id = args.user_id or None
    while not user_id:
        user_id = input("User ID (required): ").strip()

    asyncio.run(
        run_workflow(
            token=token,
            thesis=thesis,
            user_id=user_id,
        )
    )


if __name__ == "__main__":
    main()
