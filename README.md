# MOMENT AI — Meeting & Learning Intelligence

MOMENT AI turns meetings, lectures, PDFs, recordings, and notes into structured, source-grounded outputs.

## Two workflows

### Corporate
Generate minutes of meeting (MoM), executive summaries, discussion points, decisions, action items, owners, deadlines, open questions, risks, and follow-up email drafts. Unknown owners or deadlines must remain explicitly unassigned rather than guessed.

### Student
Generate topic-wise notes, explanations, definitions, formulas, examples, key takeaways, revision sheets, and practice questions.

## Inputs and outputs

**Inputs:** PDF, audio recordings, and pasted text.

**Outputs:** PDF, editable DOCX, and narrated MP3.

## Gnani model integration

- **Prisma v3.0 REST:** short-clip transcription using the project-specific API contract previously supplied (model `prisma-v3.0`, `X-API-Key-ID`).
- **Batch STT:** asynchronous upload, start, status polling, file results, and transcript download. The currently published Batch API examples specify `gnani-prisma-v2.5`; this is configurable with `GNANI_BATCH_STT_MODEL`. The Batch API has a 10 MB per-file limit, a 100-file job limit, and expiring transcript URLs.
- **Timbre v2.5 REST:** MP3 narration using binary audio responses, configurable voice, language, and speed.
- **Evon v3.3:** reasoning and structured generation. It is open-weight, not hosted on the API platform. The published model card lists Transformers 5.3+, vLLM 0.12+, or SGLang, Linux, and NVIDIA H100/H200/A100-class hardware. No unsupported hosted endpoint or local CPU compatibility is assumed.

The public Gnani documentation currently labels the generally available Prisma REST/Batch model v2.5, while the project-specific Prisma REST contract supplied for this build identifies v3.0. The code keeps these settings separate rather than silently treating the contracts as interchangeable.

## Evidence and quality rules

- Never invent attendees, decisions, action owners, due dates, formulas, or facts.
- Distinguish confirmed decisions from suggestions and discussion.
- Preserve source page references for PDF text.
- Preserve timestamps or speaker labels only when returned by the transcription service.
- Mark missing information as unknown.
- Where possible, include page or timestamp evidence alongside generated statements.

## Current implementation

- FastAPI backend with CORS configured for the local Vite frontend.
- PDF and TXT extraction with PDF page references preserved.
- Prisma v3.0 short-clip REST adapter.
- Batch STT job creation, start, status retrieval, and transcript download.
- Timbre v2.5 REST adapter returning MP3 bytes.
- Corporate and student prompt preparation endpoint (`POST /api/prepare`).
- Explicit `503` from `POST /api/process` until an Evon runtime is configured.
- PDF and editable DOCX export endpoint (`POST /api/export`).
- Mocked unit tests for the Gnani adapters and ingestion services.

These are code-level integrations and mocked tests. Real provider calls and end-to-end frontend tests still need to be run locally with the participant's API key. The React frontend is still a scaffold and is not yet connected end-to-end.

### Backend API routes

- `GET /health` — service health.
- `POST /api/ingest` — PDF/TXT extraction and short audio transcription.
- `POST /api/transcribe/batch` — upload a long recording (up to 10 MB) and start an asynchronous Batch STT job.
- `GET /api/transcribe/batch/{job_id}` — poll job status; includes transcripts when the provider marks the job `COMPLETED`.
- `POST /api/narrate` — create a narrated MP3 with Timbre v2.5.
- `POST /api/prepare` — prepare a corporate or student prompt from supplied text.
- `POST /api/process` — reserved for Evon inference; currently returns `503`.
- `POST /api/export` — create a PDF or DOCX from supplied title and text.

## Tech stack

- Frontend: React + TypeScript + Vite
- Backend: Python 3.11+ and FastAPI
- PDF extraction: PyMuPDF
- DOCX: python-docx
- PDF export: ReportLab
- Gnani speech API: requests
- Planned data layer: Firebase / Firestore

## Local setup

### Windows (PowerShell)

```powershell
cd D:\Projects\moment-ai
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn backend.app.main:app --reload
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn backend.app.main:app --reload
```

Health check: http://127.0.0.1:8000/health

API docs: http://127.0.0.1:8000/docs

Never commit real API keys. Keep them in your local `.env` file.
