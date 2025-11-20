"""Utility script to submit a task and wait for completion."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from typing import Any, Dict

from alphasanta.app import AlphaSantaApplication
from alphasanta.schema import UserLetter


async def _run(
    *,
    token: str,
    thesis: str,
    user_id: str,
    source: str,
    wallet: str | None,
    metadata: Dict[str, Any],
) -> None:
    app = AlphaSantaApplication()
    try:
        letter = UserLetter(
            token=token,
            thesis=thesis,
            user_id=user_id,
            source=source,
            metadata={"wallet_address": wallet, **metadata},
        )
        submission_id = await app.submit_letter(letter)
        print(f"Submission queued. submission_id={submission_id}")
        await app.queue.join()
        print("Task processed. Check Supabase for completed status.")
    finally:
        await app.shutdown()


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit a UserLetter and wait for completion.")
    parser.add_argument("--token", default="BANANAS31/USDT", help="Token symbol, e.g., BTC/USDT")
    parser.add_argument(
        "--thesis",
        default="The momentum is super strong",
        help="Thesis or idea text",
    )
    parser.add_argument("--user-id", help="User identifier (defaults to admin UUID)")
    parser.add_argument("--source", default="community", help="Submission source label")
    parser.add_argument("--wallet", help="Optional wallet address")
    parser.add_argument(
        "--metadata",
        help="Optional JSON string merged into UserLetter.metadata",
    )
    args = parser.parse_args()

    extra_metadata: Dict[str, Any] = {}
    if args.metadata:
        try:
            extra_metadata = json.loads(args.metadata)
        except json.JSONDecodeError as exc:
            print(f"Invalid metadata JSON: {exc}", file=sys.stderr)
            sys.exit(1)

    user_id = args.user_id or str(uuid.uuid5(uuid.NAMESPACE_DNS, "admin"))

    asyncio.run(
        _run(
            token=args.token,
            thesis=args.thesis,
            user_id=user_id,
            source=args.source,
            wallet=args.wallet,
            metadata=extra_metadata,
        )
    )


if __name__ == "__main__":
    main()
