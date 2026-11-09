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

- FastAPI backend starter.
- PDF and TXT ingestion.
- Export helpers for PDF and DOCX.
- Corporate and student prompt templates.
- Gnani API adapter placeholders pending confirmation of exact API contracts.

Audio processing and model generation are not yet fully wired. Do not present this repository as a complete working application until those integrations and end-to-end tests are complete.

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
