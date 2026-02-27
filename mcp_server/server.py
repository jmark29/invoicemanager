"""Invoice Manager MCP Server — entry point.

Run via:
    uv run python -m mcp_server.server
    uv run python -m mcp_server
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from backend.config import settings
from backend.database import engine
from backend.models import Base


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncGenerator[None, None]:
    """Ensure DB tables and data directories exist on startup."""
    Base.metadata.create_all(bind=engine)
    for directory in [
        settings.DATA_DIR,
        settings.TEMPLATES_DIR,
        settings.GENERATED_DIR,
        settings.CATEGORIES_DIR,
        settings.IMPORTS_DIR,
    ]:
        directory.mkdir(parents=True, exist_ok=True)
    yield


mcp = FastMCP(
    "Invoice Manager",
    instructions=(
        "Invoice management system for 29ventures GmbH -> DRS Holding AG. "
        "Query invoices, costs, and transactions. Generate invoices and import data. "
        "All monetary amounts are in EUR with German formatting (1.234,56 EUR). "
        "Dates in parameters use ISO format (YYYY-MM-DD), dates in output use German format (DD.MM.YYYY). "
        "Month parameters use YYYY-MM format (e.g., '2025-01')."
    ),
    lifespan=lifespan,
)

# Register tools and resources (decorators register on import)
import mcp_server.tools_query  # noqa: F401, E402
import mcp_server.tools_action  # noqa: F401, E402
import mcp_server.resources  # noqa: F401, E402


if __name__ == "__main__":
    mcp.run(transport="stdio")
