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
    alpha_signal: str | None,
    wallet: str | None,
    user_id: str | None,
) -> None:
    app = AlphaSantaApplication()
    letter = UserLetter(
        token=token,
        thesis=thesis,
        wallet_address=wallet,
        user_id=user_id,
        metadata={},
    )
    decision = await app.run_single_letter(letter, alpha_signal=alpha_signal)
    elf_reports = decision.meta.get("elf_reports", [])

    print("\n=== Elf Reports ===")
    for report in elf_reports:
        print(json.dumps(report, ensure_ascii=False, indent=2))

    print("\n=== Santa Decision ===")
    print(json.dumps(decision.to_dict(), ensure_ascii=False, indent=2))
    await app.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the AlphaSanta letter-to-decision workflow.")
    parser.add_argument("--token", help="Token symbol (e.g., BTC/USDT).")
    parser.add_argument("--thesis", help="Community thesis or signal description.")
    parser.add_argument("--wallet", help="Wallet address to bind the submission.")
    parser.add_argument("--user-id", help="Optional user identifier.")
    parser.add_argument("--alpha-signal", help="Optional proprietary alpha signal to feed AlphaElf.")
    args = parser.parse_args()

    token = args.token or input("Token symbol (e.g., BTC/USDT): ").strip()
    thesis = args.thesis or input("Thesis / idea: ").strip()
    wallet = args.wallet or input("Wallet address (optional): ").strip() or None
    user_id = args.user_id or None

    asyncio.run(
        run_workflow(
            token=token,
            thesis=thesis,
            alpha_signal=args.alpha_signal,
            wallet=wallet,
            user_id=user_id,
        )
    )


if __name__ == "__main__":
    main()
