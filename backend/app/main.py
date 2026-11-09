"""MOMENT AI FastAPI application."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .exporters import to_docx, to_pdf
from .gnani import GnaniClient
from .services.ingestion import extract_pdf, extract_text_file, get_file_extension
from .services.workflow import build_workflow_prompt

app = FastAPI(title="MOMENT AI API", version="0.2.0")
gnani = GnaniClient.from_env()
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".mp3", ".wav", ".m4a", ".ogg", ".webm"}

origins = [
    item.strip()
    for item in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if item.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ExportRequest(BaseModel):
    title: str = Field(default="MOMENT AI Output", max_length=200)
    body: str = Field(min_length=1)
    format: Literal["pdf", "docx"]


class PrepareRequest(BaseModel):
    mode: Literal["corporate", "student"]
    source_text: str = Field(min_length=1, max_length=500_000)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "moment-ai", "version": "0.2.0"}


@app.post("/api/ingest")
async def ingest(
    file: UploadFile = File(...),
    mode: Literal["corporate", "student"] = Form("corporate"),
) -> dict:
    filename = file.filename or "upload"
    suffix = get_file_extension(filename)
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Unsupported file type.")

    data = await file.read(MAX_UPLOAD_MB * 1024 * 1024 + 1)
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_UPLOAD_MB} MB.")

    if suffix == ".pdf":
        extracted = extract_pdf(data)
        source_type = "pdf"
    elif suffix == ".txt":
        extracted = extract_text_file(data)
        source_type = "text"
    else:
        raise HTTPException(
            status_code=501,
            detail="Audio transcription is not connected yet. Prisma's verified API contract is required.",
        )

    return {
        "filename": Path(filename).name,
        "mode": mode,
        "source_type": source_type,
        "character_count": len(extracted),
        "text": extracted,
    }


@app.post("/api/prepare")
def prepare_workflow(request: PrepareRequest) -> dict:
    """Build a verified workflow prompt; does not call an AI model."""
    prompt = build_workflow_prompt(request.mode, request.source_text)
    return {
        "status": "prepared",
        "mode": request.mode,
        "prompt": prompt,
        "model_status": "not_connected",
        "message": "Prompt prepared. Evon inference is not configured yet.",
    }


@app.post("/api/process")
def process_workflow(request: PrepareRequest) -> dict:
    """Reserved for model execution once an Evon runtime is configured."""
    raise HTTPException(
        status_code=503,
        detail="AI generation is not available yet. Configure a supported Evon inference runtime first.",
    )


@app.post("/api/export")
def export_document(request: ExportRequest) -> StreamingResponse:
    if request.format == "pdf":
        stream = to_pdf(request.title, request.body)
        media_type = "application/pdf"
        filename = "moment-ai-output.pdf"
    else:
        stream = to_docx(request.title, request.body)
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        filename = "moment-ai-output.docx"
    return StreamingResponse(
        stream,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
