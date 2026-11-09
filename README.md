# MOMENT AI — Meeting & Learning Intelligence

MOMENT AI turns meetings, lectures, PDFs, recordings, and notes into structured, source-grounded outputs.

## Two workflows

### Corporate
Generate minutes of meeting (MoM), executive summaries, discussion points, decisions, action items, owners, deadlines, open questions, risks, and follow-up email drafts. Unknown owners or deadlines must remain explicitly unassigned rather than guessed.

### Student
Generate topic-wise notes, explanations, definitions, formulas, examples, key takeaways, revision sheets, and practice questions.

## Inputs and outputs

**Inputs:** PDF, audio recordings, and pasted text.

**Outputs:** PDF, editable DOCX, and narrated audio.

## Gnani model integration

- **Prisma v3.0:** speech-to-text for audio transcription.
- **Evon:** reasoning and structured generation. Evon v3.3 is available as an open-weight model; this project does not assume an undocumented hosted endpoint.
- **Timbre:** text-to-speech for narrated output.

API request formats must follow the current Gnani API documentation. The adapter intentionally avoids guessing endpoint payloads.

## Evidence and quality rules

- Never invent attendees, decisions, action owners, due dates, formulas, or facts.
- Distinguish confirmed decisions from suggestions and discussion.
- Preserve source page references for PDF text.
- Preserve timestamps or speaker labels only when returned by the transcription service.
- Mark missing information as unknown.
- Where possible, include page or timestamp evidence alongside generated statements.

## Current implementation

- FastAPI backend with CORS configured for the local Vite frontend.
- PDF and TXT extraction separated into an ingestion service, with PDF page references preserved.
- Prisma v3.0 STT REST integration for audio clips up to 30 seconds, using `X-API-Key-ID`, `model=prisma-v3.0`, and configurable language/output format.
- Audio transcription metadata includes request ID, detected language, truncation flag, and provider timings.
- Upload size and file-extension validation.
- Corporate and student prompt preparation endpoint (`POST /api/prepare`). This prepares a prompt only; it does not call an LLM.
- Explicit `503` response from `POST /api/process` until a supported Evon runtime is configured.
- PDF and editable DOCX export endpoint (`POST /api/export`).
- Unit tests for ingestion and prompt preparation under `backend/tests/`.
- Gnani API adapter placeholders pending confirmation of exact API contracts.

Long-audio Batch STT, AI generation through Evon, narration through Timbre, database persistence, and end-to-end frontend integration are not yet implemented. Prisma REST currently targets clips up to 30 seconds; use the Batch API for longer recordings once its contract is implemented. Do not present this repository as a complete working application until those integrations and end-to-end tests are complete.

### Backend API routes

- `GET /health` — service health.
- `POST /api/ingest` — PDF/TXT extraction and Prisma v3.0 transcription for supported audio clips up to 30 seconds.
- `POST /api/prepare` — prepare a corporate or student prompt from supplied text.
- `POST /api/process` — reserved for Evon inference; currently returns `503`.
- `POST /api/export` — create a PDF or DOCX from supplied title and text.

## Tech stack

- Frontend: React + TypeScript + Vite
- Backend: Python 3.11+ and FastAPI
- PDF extraction: PyMuPDF
- DOCX: python-docx
- PDF export: ReportLab
- Planned data layer: Firebase / Firestore

## Architecture

See [docs/architecture.md](docs/architecture.md) for the eight logical layers, request flows, repository structure, and design rules.

The React + TypeScript frontend scaffold is in `frontend/`. Firebase/Firestore persistence is planned but not connected yet. See [docs/architecture.md](docs/architecture.md) for the target modular-monolith design.

## Local setup

### Windows (PowerShell)

```powershell
cd moment-ai
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn backend.app.main:app --reload
```

### macOS / Linux

```bash
cd moment-ai
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn backend.app.main:app --reload
```

Health check: http://127.0.0.1:8000/health

API docs: http://127.0.0.1:8000/docs

Never commit real API keys. Keep them in your local `.env` file.
