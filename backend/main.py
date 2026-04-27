"""FastAPI main application — Notes Generator backend."""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Load environment
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

from .api import jobs, entries, downloads, settings
from .core.llm_clients import LLMClients
from .core.orchestrator import JobOrchestrator
from .core.screenshot import close_browser
from .db.repo import Database

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "../output/app.sqlite")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "../output")

# Resolve relative paths from the backend directory
backend_dir = Path(__file__).parent
db_path = str((backend_dir / DB_PATH).resolve())
output_dir = str((backend_dir / OUTPUT_DIR).resolve())


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown."""
    log.info("Starting Notes Generator backend...")
    log.info("DB path: %s", db_path)
    log.info("Output dir: %s", output_dir)

    # Initialize database
    db = Database(db_path)
    await db.connect()
    app.state.db = db

    # Initialize LLM clients
    llm = LLMClients()
    app.state.llm_clients = llm
    log.info("Available LLM providers: %s", llm.get_available_providers())

    # Initialize orchestrator
    orchestrator = JobOrchestrator(db, llm, output_dir)
    app.state.orchestrator = orchestrator

    yield

    # Shutdown
    log.info("Shutting down...")
    await close_browser()
    await db.close()


app = FastAPI(
    title="Notes Generator",
    description="Generate training data for People & Relationships notes",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(jobs.router)
app.include_router(entries.router)
app.include_router(downloads.router)
app.include_router(settings.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "notes-generator"}
