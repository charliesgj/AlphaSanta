"""
Utility helpers for running AgentCard servers via uvicorn.
"""

from __future__ import annotations

import asyncio

import uvicorn

from alphasanta.agentcard import CardConfig, build_agentcard_server


async def serve_agentcard(config: CardConfig, executor) -> None:
    """
    Spin up an AgentCard server with the given executor.
    """
    application = build_agentcard_server(config=config, executor=executor)
    uvicorn_config = uvicorn.Config(
        app=application.build(),
        host=config.host,
        port=config.port,
        log_level="info",
        loop="asyncio",
    )
    server = uvicorn.Server(uvicorn_config)
    await server.serve()


def run_agentcard(config: CardConfig, executor) -> None:
    """
    Blocking runner used by CLI entrypoints.
    """
    asyncio.run(serve_agentcard(config, executor))
