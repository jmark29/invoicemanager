from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import engine
from backend.models import Base


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


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
