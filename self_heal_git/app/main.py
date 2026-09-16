from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from sqlmodel import SQLModel

from app.config import settings, engine
from app.models import User, Repository, PRRecord, PRRun
from app.api import router as api_router
from app.routes.auth_routes import router as auth_router
from app.routes.admin_routes import router as admin_router

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


from app.watcher import start_event_driven_watcher, stop_event_driven_watcher

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    create_db_and_tables()
    start_event_driven_watcher()
    yield
    stop_event_driven_watcher()


# Guarantee tables exist in self_heal_git.db upon module import
create_db_and_tables()


# Initialize FastAPI app with modern lifespan handler
app = FastAPI(
    title="Self-Heal Git",
    description="Autonomous PR Reviewer, Bug Fixer, and Self-Healing Engine with RBAC, JWT, and Google OAuth",
    version="0.3.0",
    lifespan=lifespan,
)

# Enable CORS for Next.js frontend
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API, Auth, and Admin routers
app.include_router(auth_router)
app.include_router(api_router)
app.include_router(admin_router)


@app.get("/", summary="Root Health & Service Info")
def root_status():
    return {
        "status": "online",
        "service": "Self-Heal Git API",
        "version": "0.3.0",
        "interactive_docs": "/docs",
        "frontend_dashboard": "http://localhost:3000/dashboard",
        "three_agent_pipeline": {
            "benchmark_trigger": "POST /api/pipeline/benchmark",
            "custom_run": "POST /api/pipeline/run",
            "latest_trace": "GET /api/pipeline/latest-trace",
            "agents": [
                "Agent 1: Test Runner & CI Failure Interceptor",
                "Agent 2: Stack Trace Diagnostic & Surgical Code Repair",
                "Agent 3: Verification & Regression Agent (100% Pass)",
            ],
        },
    }

