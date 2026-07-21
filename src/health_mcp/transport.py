"""Dual transport for health-mcp."""

import asyncio
import logging
from typing import Any

from fastmcp import FastMCP

logger = logging.getLogger(__name__)

ENV_TRANSPORT = "MCP_TRANSPORT"
ENV_HOST = "MCP_HOST"
ENV_PORT = "MCP_PORT"
ENV_PATH = "MCP_PATH"


def get_transport_config() -> dict[str, Any]:
    import os
    return {
        "transport": os.getenv(ENV_TRANSPORT, "stdio"),
        "host": os.getenv(ENV_HOST, "127.0.0.1"),
        "port": int(os.getenv(ENV_PORT, "10902")),
        "path": os.getenv(ENV_PATH, "/mcp"),
    }


def run_server(app: FastMCP, server_name: str = "health-mcp"):
    config = get_transport_config()
    transport = config["transport"]
    logger.info("Starting %s (%s transport)", server_name, transport)

    if transport == "stdio":
        app.run()
    elif transport == "http":
        import uvicorn
        from fastapi.middleware.cors import CORSMiddleware
        http_app = app.http_app()
        http_app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        uvicorn.run(http_app, host=config["host"], port=config["port"], log_level="info")
    elif transport == "sse":
        asyncio.run(app.run_sse_async(host=config["host"], port=config["port"]))
    else:
        logger.error("Unknown transport: %s", transport)


def main():
    from .server import app
    run_server(app)
