import logging
import shutil
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

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
    settings as settings_router,
    upwork_transactions,
    working_days,
)

logger = logging.getLogger(__name__)

# Mapping from reference-docs subdirectory to category_id for PDF copy
_REFERENCE_PDF_SOURCES = {
    "junior_fm": Path("docs/reference-docs/Junior FM"),
    "aeologic": Path("docs/reference-docs/Aeologic"),
    "cloud_engineer": Path("docs/reference-docs/Kaletsch - Cloud engineer"),
}

# Seed file_path corrections: old (wrong) -> new (correct) for existing DBs
_FILE_PATH_CORRECTIONS = {
    "categories/junior_fm/ER2504-11.pdf": "categories/junior_fm/ER2504-03.pdf",
    "categories/junior_fm/ER2505-16.pdf": "categories/junior_fm/ER2505-19.pdf",
    "categories/junior_fm/ER2507-04.pdf": "categories/junior_fm/ER2507-18.pdf",
    "categories/junior_fm/ER2508-12.pdf": "categories/junior_fm/ER2508-17.pdf",
    "categories/junior_fm/ER2509-08.pdf": "categories/junior_fm/ER2509-16.pdf",
    "categories/junior_fm/ER2510-02.pdf": "categories/junior_fm/ER2510-18.pdf",
    "categories/junior_fm/ER2511-12.pdf": "categories/junior_fm/ER2511-17.pdf",
}


def _copy_reference_pdfs() -> None:
    """Copy reference PDFs from docs/reference-docs/ into data/categories/ if not already present."""
    for category_id, source_dir in _REFERENCE_PDF_SOURCES.items():
        if not source_dir.exists():
            continue
        dest_dir = settings.CATEGORIES_DIR / category_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        for pdf in source_dir.glob("*.pdf"):
            dest = dest_dir / pdf.name
            if not dest.exists():
                shutil.copy2(pdf, dest)
                logger.info("Copied reference PDF: %s -> %s", pdf.name, dest)


def _fix_stale_file_paths(db: Session) -> None:
    """Fix file_path values in existing DB records that reference old/wrong filenames."""
    from backend.models.provider_invoice import ProviderInvoice

    fixed = 0
    for old_path, new_path in _FILE_PATH_CORRECTIONS.items():
        inv = db.query(ProviderInvoice).filter(ProviderInvoice.file_path == old_path).first()
        if inv:
            inv.file_path = new_path
            fixed += 1
    if fixed:
        db.commit()
        logger.info("Fixed %d stale provider_invoice file_path values", fixed)


def _auto_link_pdfs(db: Session) -> None:
    """Auto-link provider invoices with missing file_path to PDFs found on disk.

    Scans data/categories/{category_id}/ for PDFs whose filename contains the
    invoice number. Handles cases where seed data didn't set file_path but
    reference PDFs were copied to disk.
    """
    from backend.models.provider_invoice import ProviderInvoice

    invoices = db.query(ProviderInvoice).filter(
        ProviderInvoice.file_path.is_(None)
    ).all()

    linked = 0
    for inv in invoices:
        cat_dir = settings.CATEGORIES_DIR / inv.category_id
        if not cat_dir.exists():
            continue
        inv_num_lower = inv.invoice_number.lower().replace("/", "-")
        for pdf in cat_dir.glob("*.pdf"):
            pdf_name_lower = pdf.name.lower()
            if inv_num_lower in pdf_name_lower or inv.invoice_number.lower() in pdf_name_lower:
                rel_path = str(pdf.relative_to(settings.DATA_DIR))
                inv.file_path = rel_path
                linked += 1
                logger.info("Auto-linked invoice %s -> %s", inv.invoice_number, rel_path)
                break
    if linked:
        db.commit()
        logger.info("Auto-linked %d provider invoices to PDF files on disk", linked)


def _validate_file_paths(db: Session) -> None:
    """Log warnings for provider invoices whose file_path points to a missing file."""
    from backend.models.provider_invoice import ProviderInvoice

    invoices = db.query(ProviderInvoice).filter(ProviderInvoice.file_path.isnot(None)).all()
    for inv in invoices:
        full_path = settings.DATA_DIR / inv.file_path
        if not full_path.exists():
            logger.warning(
                "Provider invoice %s (id=%d) references missing file: %s",
                inv.invoice_number, inv.id, inv.file_path,
            )


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

    # Copy reference PDFs to data/categories/ and fix stale/missing file_path values
    _copy_reference_pdfs()
    db = SessionLocal()
    try:
        _fix_stale_file_paths(db)
        _auto_link_pdfs(db)
        _validate_file_paths(db)
    finally:
        db.close()

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
app.include_router(settings_router.router)
app.include_router(backup.router)


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
