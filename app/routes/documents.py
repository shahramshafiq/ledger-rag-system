import asyncio
import json
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from app.chunking.structure_aware import chunk_structure_aware
from app.services.ingestion_service import ingest_filing

logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# in-memory job store: job_id -> {"status", "message", "chunks"}. Fine for a single
# process; a multi-worker deployment would need a shared store here instead (the same
# role Valkey plays in Project 1), not needed for ingesting one filing at a time.
JOBS = {}


@router.post("/documents")
async def post_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    company: str = Form(...),
    ticker: str = Form(...),
    fiscal_year: str = Form(...),
    form_type: str = Form("10-K"),
):
    if not file.filename.lower().endswith((".html", ".htm")):
        return JSONResponse(
            content={"error": "UNSUPPORTED_FILE_TYPE", "message": "Only .html/.htm filings are supported"},
            status_code=415,
        )

    job_id = str(uuid.uuid4())
    saved_path = UPLOAD_DIR / f"{job_id}.html"
    saved_path.write_bytes(await file.read())

    JOBS[job_id] = {"status": "queued", "message": "Waiting to start", "chunks": None}
    background_tasks.add_task(run_ingestion, job_id, str(saved_path), company, ticker, fiscal_year, form_type)

    return {"job_id": job_id, "status": "queued"}


def run_ingestion(job_id, html_path, company, ticker, fiscal_year, form_type):
    JOBS[job_id] = {"status": "processing", "message": "Parsing and chunking filing", "chunks": None}

    try:
        chunk_count = ingest_filing(html_path, company, ticker, fiscal_year, chunk_structure_aware, form_type=form_type)
        JOBS[job_id] = {"status": "completed", "message": f"Ingested {chunk_count} chunks", "chunks": chunk_count}

    except (ValueError, RuntimeError) as e:
        JOBS[job_id] = {"status": "failed", "message": str(e), "chunks": None}

    except Exception:
        logger.exception(f"Ingestion failed for job {job_id}")
        JOBS[job_id] = {"status": "failed", "message": "Unexpected error during ingestion", "chunks": None}


@router.get("/documents/{job_id}/stream")
async def stream_document_status(job_id: str):
    if job_id not in JOBS:
        return JSONResponse(
            content={"error": "JOB_NOT_FOUND", "message": "No ingestion job with this ID"},
            status_code=404,
        )

    async def event_generator():
        last_data = None
        try:
            while True:
                job = JOBS.get(job_id)
                if job is None:
                    return

                data = {"job_id": job_id, **job}
                if data != last_data:
                    yield f"data: {json.dumps(data)}\n\n"
                    last_data = data

                if job["status"] in ("completed", "failed"):
                    return

                await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info(f"SSE client disconnected from job {job_id}")
            raise

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )