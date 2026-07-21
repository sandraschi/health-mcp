"""health-mcp FastMCP server."""

import logging
from contextlib import asynccontextmanager

from fastmcp import FastMCP

from .services.health_store import get_store
from .tools.health_tools import register_health_tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def server_lifespan(mcp: FastMCP):
    logger.info("health-mcp starting...")
    store = get_store()
    logger.info("Health store ready: %s (%d records)", store._db_path, store.get_stats()["health_records"])
    yield
    logger.info("health-mcp shutting down...")


app = FastMCP(
    name="health-mcp",
    instructions="""Health-MCP: Multi-source health data fusion.

CORE CAPABILITIES:
- Store health metrics (weight, HR, sleep, meals, steps, BP, mood)
- Import Apple Health exports (XML/zip)
- Receive VSM events from devices-mcp (camera-based state machines)
- Trend analysis over configurable time windows
- Pet health tracking (feeding, activity)
- Prefab UI dashboard for recent stats

EVENT SOURCES:
- manual: direct tool calls from agents or chat
- vsm: camera-based Visual State Machine events (devices-mcp)
- apple_health: iOS Health app XML export
- api: REST ingestion endpoint

TOOLS:
- health_data: Log, query, trend, import records
- show_health_dashboard: Rich summary card""",
    lifespan=server_lifespan,
    strict_input_validation=True,
    on_duplicate="replace",
)

register_health_tools(app)

try:
    from .tools._prefab import register_prefab_tools
    register_prefab_tools(app)
    logger.info("Prefab UI tools registered")
except ImportError:
    pass


def main():
    from .transport import run_server
    run_server(app, server_name="health-mcp")


if __name__ == "__main__":
    main()
