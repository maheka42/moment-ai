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
- **Hosted LLM:** reasoning and structured generation through an OpenAI-compatible chat-completions API. The default configuration targets Groq `openai/gpt-oss-120b`; configure `LLM_API_URL`, `LLM_API_KEY`, and `LLM_MODEL`. No local GPU deployment is required.

The public Gnani documentation and challenge page currently describe Prisma v2.5, while the project-specific Prisma REST contract supplied for this build identifies v3.0. Short-clip REST model selection is configurable with `GNANI_PRISMA_MODEL`; set it to an empty value to omit the model field and use the account's default. Batch STT remains separately configured because its public contract specifies v2.5.

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
- Hosted LLM generation adapter for an OpenAI-compatible chat-completions endpoint (default: Groq GPT OSS 120B); returns `503` until the endpoint and API key are configured.
- PDF, editable DOCX, and Timbre MP3 export endpoints.
- React frontend connected to ingestion, Batch STT, hosted LLM generation, PDF/DOCX export, and MP3 narration.
- Mocked unit tests for the Gnani adapters and ingestion services.

These are code-level integrations and mocked tests. Real Gnani and Groq provider calls and end-to-end tests still need to be run locally with the participant's API keys.

### Backend API routes

- `GET /health` — service health.
- `POST /api/ingest` — PDF/TXT extraction and short audio transcription.
- `POST /api/transcribe/batch` — upload a long recording (up to 10 MB) and start an asynchronous Batch STT job.
- `GET /api/transcribe/batch/{job_id}` — poll job status; includes completed transcripts and failed-file details for terminal jobs.
- `POST /api/narrate` — create a narrated MP3 with Timbre v2.5.
- `POST /api/prepare` — prepare a corporate or student prompt from supplied text.
- `POST /api/process` — generate the selected corporate/student output with the configured hosted LLM; returns `503` until `LLM_API_URL` and `LLM_API_KEY` are configured.
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
# Copy the example only when .env does not already exist.
if (!(Test-Path .env)) { Copy-Item .env.example .env }
python -m unittest discover -s backend/tests -v
uvicorn backend.app.main:app --reload
```

In a second PowerShell terminal, start the frontend:

```powershell
cd D:\Projects\moment-ai\frontend
npm install --cache D:\Projects\.npm-cache
npm run build
npm run dev
```

Copy `frontend/.env.example` to `frontend/.env` only if you need to change the backend URL. If `.env` already exists, edit it rather than replacing it. Set `GNANI_API_KEY_ID` to your private API key. Set `LLM_API_KEY` to your Groq API key. The default `LLM_API_URL` and `LLM_MODEL` target Groq GPT OSS 120B. Keep all API keys in the local `.env` file; never commit them.

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
