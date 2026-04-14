import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import diagnose, dtc, documents, torque
from app.config import get_settings
from app.core.auto_ingest import start_auto_ingest_loop
from app.core.torque_db import load_specs

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load torque specs and start auto-ingest watcher
    specs = load_specs()
    logger.info(f"Loaded {len(specs)} torque specs from database")

    settings = get_settings()
    ingest_task = asyncio.create_task(
        start_auto_ingest_loop(settings.auto_ingest_interval_seconds)
    )

    yield

    # Shutdown: cancel background tasks
    ingest_task.cancel()
    try:
        await ingest_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="AI Auto Diag",
    description="AI-powered automotive diagnostic assistant using Claude API + RAG",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow Streamlit and local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(diagnose.router, prefix="/api", tags=["Diagnostics"])
app.include_router(dtc.router, prefix="/api", tags=["DTC Codes"])
app.include_router(documents.router, prefix="/api", tags=["Documents"])
app.include_router(torque.router, prefix="/api", tags=["Torque Specs"])


@app.get("/")
async def root():
    return {
        "service": "AI Auto Diag",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
