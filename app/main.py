from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.certificates import router as certificates_router
from app.api.routes.jobs import router as jobs_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import init_db

configure_logging()

app = FastAPI(
    title="Bulk Certificate Generator API",
    version="1.0.0",
    description="Generate and manage bulk certificate jobs with per-recipient validation and processing results.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_router)
app.include_router(certificates_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Bulk Certificate Generator API is running."}
