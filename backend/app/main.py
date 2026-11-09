"""MOMENT AI API starter."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Literal

import fitz
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .exporters import to_docx, to_pdf
from .gnani import GnaniClient

app = FastAPI(title="MOMENT AI API", version="0.1.0")
gnani = GnaniClient.from_env()
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".mp3", ".wav", ".m4a", ".ogg", ".webm"}


class ExportRequest(BaseModel):
    title: str = Field(default="MOMENT AI Output", max_length=200)
    body: str = Field(min_length=1)
    format: Literal["pdf", "docx"]


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "moment-ai"}


def extract_pdf(data: bytes) -> str:
    pages: list[str] = []
    try:
        with fitz.open(stream=data, filetype="pdf") as pdf:
            for page_number, page in enumerate(pdf, start=1):
                text = page.get_text("text").strip()
                if text:
                    pages.append(f"[Source: page {page_number}]\n{text}")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not read this PDF.") from exc
    return "\n\n".join(pages)


@app.post("/api/ingest")
async def ingest(
    file: UploadFile = File(...),
    mode: Literal["corporate", "student"] = Form("corporate"),
) -> dict:
    filename = file.filename or "upload"
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Unsupported file type.")
    data = await file.read()
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_UPLOAD_MB} MB.")
    if suffix == ".pdf":
        extracted = extract_pdf(data)
        return {"filename": filename, "mode": mode, "source_type": "pdf", "text": extracted}
    if suffix == ".txt":
        try:
            extracted = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail="TXT file must be UTF-8 encoded.") from exc
        return {"filename": filename, "mode": mode, "source_type": "text", "text": extracted}
    raise HTTPException(
        status_code=501,
        detail="Audio ingestion is not connected yet. Prisma API contract must be implemented first.",
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
