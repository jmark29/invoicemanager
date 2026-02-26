from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import engine
from backend.models import Base
from backend.routers import (
    bank_transactions,
    clients,
    cost_categories,
    invoices,
    line_item_definitions,
    payments,
    provider_invoices,
    upwork_transactions,
    working_days,
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Ensure data directories exist
    for directory in [
        settings.DATA_DIR,
        settings.TEMPLATES_DIR,
        settings.GENERATED_DIR,
        settings.CATEGORIES_DIR,
        settings.IMPORTS_DIR,
    ]:
        directory.mkdir(parents=True, exist_ok=True)

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


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
