"""CLI entry point to drain pending submissions from Supabase."""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
from contextlib import suppress

from alphasanta.app import AlphaSantaApplication
from alphasanta.services import SubmissionWorker


async def _serve(poll_interval: float) -> None:
    app = AlphaSantaApplication()
    worker = SubmissionWorker(app, poll_interval=poll_interval)

    loop = asyncio.get_running_loop()

    def _stop_worker() -> None:
        worker.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, _stop_worker)

    try:
        await worker.run_forever()
    finally:
        for sig in (signal.SIGINT, signal.SIGTERM):
            with suppress(NotImplementedError):
                loop.remove_signal_handler(sig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Process pending submissions from Supabase.")
    parser.add_argument(
        "--interval",
        type=float,
        default=3.0,
        help="Polling interval in seconds when the queue is empty (default: 3s).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ...).",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    try:
        asyncio.run(_serve(args.interval))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
