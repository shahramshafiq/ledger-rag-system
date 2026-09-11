import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.routes import documents, query
from app.utils.logging import setup_logging
from app.vectorstore.store import get_vector_store

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    try:
        get_vector_store()
        logger.info("Connected to Postgres on startup")
    except RuntimeError as e:
        logger.error(f"Postgres not reachable on startup: {e}")
    yield
    logger.info("Application shutting down")


app = FastAPI(title="Ledger", lifespan=lifespan)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unexpected error handling {request.method} {request.url.path}: {exc}")
    return JSONResponse(
        content={"error": "INTERNAL_SERVER_ERROR", "message": "An unexpected error occurred"},
        status_code=500,
    )


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/health/ready")
def health_ready():
    try:
        get_vector_store()
        return {"status": "ready", "database": "available"}
    except RuntimeError:
        return JSONResponse(
            content={"status": "not ready", "database": "unavailable"},
            status_code=503,
        )


app.include_router(documents.router)
app.include_router(query.router)