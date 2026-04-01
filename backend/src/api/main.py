"""
FinBot FastAPI application entry point.

Starts the API server with all routes mounted.
CORS configured for Next.js frontend on port 3000.

Usage:
    cd backend/
    uv run --active uvicorn src.api.main:app --reload --port 8000
    # or:
    make dev
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.auth  import router as auth_router
from src.api.routes.chat  import router as chat_router
from src.api.routes.admin import router as admin_router

logging.basicConfig(
    level="INFO",
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="FinBot API",
    description=(
        "Advanced RAG system for FinSolve Technologies "
        "with RBAC, semantic routing, and guardrails."
    ),
    version="1.0.0",
    docs_url="/docs",      # Swagger UI at /docs
    redoc_url="/redoc",    # ReDoc at /redoc
)

# CORS — allow Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://localhost:3000",
        "*",  # for Codespaces — restrict in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(admin_router)


@app.get("/")
def root():
    return {
        "service":     "FinBot API",
        "version":     "1.0.0",
        "status":      "online",
        "docs":        "/docs",
        "description": "Advanced RAG with RBAC for FinSolve Technologies",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
async def startup_event():
    logger.info("="*50)
    logger.info("  FinBot API starting up...")
    logger.info("  Docs available at: /docs")
    logger.info("="*50)