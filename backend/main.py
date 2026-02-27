import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from alembic import command
from alembic.config import Config

from backend.config import settings
from backend.logging_config import setup_logging
from backend.models import Base  # noqa: F401 — ensures metadata is populated
from backend.routers import (
    backup,
    bank_transactions,
    clients,
    cost_categories,
    dashboard,
    invoices,
    line_item_definitions,
    payments,
    provider_invoices,
    upwork_transactions,
    working_days,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging(settings.LOG_LEVEL)

    # Run database migrations
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

    # Auto-seed on first startup (idempotent — skips if data exists)
    from backend.seed.loader import seed_all
    from backend.database import SessionLocal

    db = SessionLocal()
    try:
        if seed_all(db):
            logger.info("Seed data loaded on first startup")
    finally:
        db.close()

    # Ensure data directories exist
    for directory in [
        settings.DATA_DIR,
        settings.TEMPLATES_DIR,
        settings.GENERATED_DIR,
        settings.CATEGORIES_DIR,
        settings.IMPORTS_DIR,
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    # Check WeasyPrint availability
    try:
        from weasyprint import HTML
        HTML(string="<html><body>ok</body></html>").write_pdf()
        logger.info("WeasyPrint PDF rendering: OK")
    except Exception as e:
        logger.warning(
            "WeasyPrint PDF rendering unavailable: %s. "
            "Invoice PDF generation will fail. "
            "Fix: brew install pango cairo libffi && "
            "export DYLD_LIBRARY_PATH=/opt/homebrew/lib",
            e,
        )

    logger.info("Invoice Manager started (data_dir=%s)", settings.DATA_DIR)
    yield


app = FastAPI(
    title="Invoice Manager",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(clients.router)
app.include_router(cost_categories.router)
app.include_router(line_item_definitions.router)
app.include_router(provider_invoices.router)
app.include_router(bank_transactions.router)
app.include_router(upwork_transactions.router)
app.include_router(invoices.router)
app.include_router(payments.router)
app.include_router(working_days.router)
app.include_router(dashboard.router)
app.include_router(backup.router)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
