"""MOMENT AI FastAPI application."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from .exporters import to_docx, to_pdf
from .gnani import GnaniAPIError, GnaniClient
from .services.ingestion import extract_pdf, extract_text_file, get_file_extension
from .services.workflow import build_workflow_prompt

# Load local development secrets before creating provider clients.
load_dotenv()

app = FastAPI(title="MOMENT AI API", version="0.4.0")
gnani = GnaniClient.from_env()
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"}

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


class NarrateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=100_000)
    voice: str = Field(default="Nalini", max_length=40)
    language: str = Field(default="auto", max_length=10)
    speed: float = Field(default=1.0, ge=0.85, le=1.15)


def _raise_gnani_http_error(exc: Exception) -> None:
    if isinstance(exc, RuntimeError):
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if isinstance(exc, GnaniAPIError):
        status = exc.status_code if 400 <= exc.status_code < 600 else 502
        raise HTTPException(
            status_code=status,
            detail={"message": str(exc), "error_type": exc.error_type},
        ) from exc
    raise HTTPException(status_code=502, detail="Gnani API request failed.") from exc


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "moment-ai",
        "version": "0.4.0",
        "integrations": {
            "prisma_rest": bool(gnani.api_key_id and gnani.stt_endpoint),
            "batch_stt": bool(gnani.api_key_id),
            "timbre": bool(gnani.api_key_id and gnani.tts_endpoint),
            "llm": bool(gnani.llm_endpoint and gnani.llm_api_key),
        },
    }


@app.post("/api/ingest")
async def ingest(
    file: UploadFile = File(...),
    mode: Literal["corporate", "student"] = Form("corporate"),
    language_code: str = Form("indic-auto"),
    audio_format: Literal["verbatim", "transcribe", "codemix", "transliterate"] = Form("transcribe"),
    topic: str | None = Form(None),
) -> dict:
    filename = Path(file.filename or "upload").name
    suffix = get_file_extension(filename)
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Unsupported file type.")

    data = await file.read(MAX_UPLOAD_MB * 1024 * 1024 + 1)
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_UPLOAD_MB} MB.")

    if suffix == ".pdf":
        extracted = extract_pdf(data)
        source_type = "pdf"
        metadata = {}
    elif suffix == ".txt":
        extracted = extract_text_file(data)
        source_type = "text"
        metadata = {}
    else:
        try:
            transcription = gnani.transcribe_with_prisma(
                audio_bytes=data, filename=filename, language_code=language_code,
                output_format=audio_format, topic=topic,
            )
        except (RuntimeError, ValueError, GnaniAPIError) as exc:
            _raise_gnani_http_error(exc)
        extracted = transcription["transcript"]
        source_type = "audio"
        metadata = {
            "model": transcription.get("model"),
            "request_id": transcription.get("request_id"),
            "detected_language_code": transcription.get("detected_language_code"),
            "truncated": transcription.get("truncated", False),
            "processing_time": transcription.get("processing_time"),
            "end_to_end_latency": transcription.get("end_to_end_latency"),
            "transcription_mode": "rest",
        }

    return {
        "filename": filename, "mode": mode, "source_type": source_type,
        "character_count": len(extracted), "text": extracted, "metadata": metadata,
    }


@app.post("/api/transcribe/batch")
async def create_batch_transcription(
    file: UploadFile = File(...),
    language_code: str = Form("en-IN"),
) -> dict:
    """Create and start an asynchronous Batch STT job for a long recording."""
    filename = Path(file.filename or "recording").name
    if get_file_extension(filename) not in {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"}:
        raise HTTPException(status_code=415, detail="Batch transcription accepts audio files only.")
    data = await file.read(10 * 1024 * 1024 + 1)
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Batch STT accepts files up to 10 MB.")
    try:
        job = gnani.create_batch_job(data, filename, language_code)
        started = gnani.start_batch_job(job["job_id"])
    except (RuntimeError, ValueError, GnaniAPIError) as exc:
        _raise_gnani_http_error(exc)
    return {
        "job_id": job["job_id"],
        "status": started.get("status", job.get("status", "CREATED")),
        "message": "Batch transcription started. Poll the job status endpoint for results.",
        "model": gnani.batch_stt_model,
    }


@app.get("/api/transcribe/batch/{job_id}")
def get_batch_transcription(job_id: str) -> dict:
    """Return batch progress and transcripts once Gnani marks the job complete."""
    if not job_id or len(job_id) > 100 or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in job_id):
        raise HTTPException(status_code=400, detail="Invalid batch job ID.")
    try:
        status = gnani.get_batch_job(job_id)
        job_status = str(status.get("status", "UNKNOWN")).upper()
        result = {"job_id": job_id, "status": job_status, "provider": status}
        if job_status in {"COMPLETED", "PARTIAL_FAILURE", "FAILED"}:
            files_payload = gnani.get_batch_files(job_id)
            transcripts = []
            for item in files_payload.get("data", []):
                transcript_url = item.get("transcript_url")
                if item.get("status") == "COMPLETED" and transcript_url:
                    transcript = gnani.download_batch_transcript(transcript_url)
                    transcripts.append({
                        "filename": item.get("original_path"),
                        "duration_seconds": transcript.get("duration_seconds"),
                        "language_code": transcript.get("language_code"),
                        "model": transcript.get("model"),
                        "text": transcript["full_transcript"],
                        "segments": transcript.get("segments", []),
                    })
            result["transcripts"] = transcripts
            result["file_results"] = files_payload.get("data", [])
        return result
    except (RuntimeError, ValueError, GnaniAPIError) as exc:
        _raise_gnani_http_error(exc)


@app.post("/api/narrate")
def narrate(request: NarrateRequest) -> StreamingResponse:
    """Create an MP3 narration using Gnani Timbre v2.5."""
    try:
        audio = gnani.synthesize_with_timbre(
            text=request.text, voice=request.voice, language=request.language,
            speed=request.speed, container="mp3",
        )
    except (RuntimeError, ValueError, GnaniAPIError) as exc:
        _raise_gnani_http_error(exc)
    return StreamingResponse(
        iter([audio]), media_type="audio/mpeg",
        headers={"Content-Disposition": 'attachment; filename="moment-ai-narration.mp3"'},
    )


@app.post("/api/prepare")
def prepare_workflow(request: PrepareRequest) -> dict:
    """Build a verified workflow prompt; does not call an AI model."""
    prompt = build_workflow_prompt(request.mode, request.source_text)
    return {
        "status": "prepared", "mode": request.mode, "prompt": prompt,
        "model_status": "not_connected",
        "message": "Prompt prepared. Hosted LLM generation is not configured yet.",
    }


@app.post("/api/process")
def process_workflow(request: PrepareRequest) -> dict:
    """Generate corporate or student output with the configured hosted LLM."""
    prompt = build_workflow_prompt(request.mode, request.source_text)
    try:
        generated = gnani.generate_with_llm(prompt)
    except (RuntimeError, ValueError, GnaniAPIError) as exc:
        _raise_gnani_http_error(exc)
    return {
        "status": "completed",
        "mode": request.mode,
        "model": gnani.llm_model,
        "output": generated,
    }


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
        stream, media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
