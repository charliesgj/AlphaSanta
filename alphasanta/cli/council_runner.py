"""Deprecated shim for the old `alphasanta-run-council` entrypoint."""

from __future__ import annotations

import warnings

from .start import main as start_main, run_workflow as run_workflow


async def run_council(**kwargs):
    warnings.warn(
        "`alphasanta-run-council` is deprecated, use `alphasanta-start` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return await run_workflow(**kwargs)


def main() -> None:
    warnings.warn(
        "`alphasanta-run-council` is deprecated, use `alphasanta-start` instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    start_main()


if __name__ == "__main__":
    main()
