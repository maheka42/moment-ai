# MOMENT AI — Architecture

## Architecture decision

Start with a **modular monolith**: one React web client and one FastAPI backend, organized into clear internal modules. Do not split into microservices for the MVP.

## Logical layers

1. **Frontend** — React + TypeScript + Vite; user interface and upload interactions.
2. **API layer** — FastAPI routes; request validation and response handling.
3. **Ingestion layer** — PDF, text, short audio, and long audio input handling; preserve page/timestamp provenance when the source provides it.
4. **AI integration layer** — isolated Gnani adapters for Prisma short-clip REST, Prisma Batch STT, and Timbre REST, plus a configurable hosted OpenAI-compatible LLM client (default: Groq GPT OSS 120B).
5. **Workflow/business layer** — corporate meeting minutes and student study-notes workflows with source-grounding rules.
6. **Export layer** — PDF, DOCX, and narrated MP3 output.
7. **Data layer** — Firebase/Firestore is planned for user data and document metadata; storage design will be finalized before persistence is implemented.
8. **Security/configuration layer** — environment-based secrets, upload limits, CORS, validation, access control, and retention.

## Provider API contracts in use

- **Authentication:** `X-API-Key-ID` header; the key stays in the backend environment.
- **Prisma short-clip REST:** `POST /stt/v3`. The project-specific contract supplied for this build uses `model=prisma-v3.0`, configurable through `GNANI_PRISMA_MODEL`. The current public Gnani docs describe v2.5 and short clips up to 60 seconds (30 seconds ideal); setting `GNANI_PRISMA_MODEL` empty omits the model field and uses the account default. Verify the actual account entitlement during real API testing.
- **Batch STT:** `POST /stt/v3/batch/jobs`, then `POST /{job_id}/start`, poll `GET /{job_id}`, fetch `GET /{job_id}/files`, and download each short-lived `transcript_url`. Public Batch docs currently specify `gnani-prisma-v2.5`, 10 MB per file, and up to 100 files per job. This is separately configurable.
- **Timbre:** `POST /api/v1/tts/inference`, model `timbre-v2.5`; the endpoint returns binary audio. MOMENT AI requests MP3 for narration.
- **Hosted LLM:** MOMENT AI calls an OpenAI-compatible chat-completions endpoint. The default is Groq `openai/gpt-oss-120b`, configured through `LLM_API_URL`, `LLM_API_KEY`, and `LLM_MODEL`. No self-hosted GPU is required. Do not silently fall back to a different model.

## Request flows

### Corporate
Meeting recording → Prisma short-clip REST or Batch STT → evidence-grounded meeting workflow using the configured hosted LLM → reviewable MoM → PDF/DOCX export and optional Timbre narration.

### Student
Lecture recording/PDF/text → extraction or Prisma transcription → evidence-grounded study workflow using Evon → reviewable notes → PDF/DOCX export and optional Timbre narration.

## Current backend routes

- `GET /health`
- `POST /api/ingest` — PDF/TXT extraction and short-clip audio transcription.
- `POST /api/transcribe/batch` — upload and start an asynchronous Batch STT job.
- `GET /api/transcribe/batch/{job_id}` — retrieve job state and completed transcripts.
- `POST /api/narrate` — return an MP3 narration from Timbre v2.5.
- `POST /api/prepare` — prepare the corporate/student prompt; no model call.
- `POST /api/process` — generate the corporate/student output with the configured hosted LLM; returns 503 until its endpoint and API key are configured.
- `POST /api/export` — PDF or DOCX.

## Proposed repository layout

```text
moment-ai/
├── frontend/                 # React + TypeScript + Vite
│   └── src/
├── backend/
│   └── app/
│       ├── api/              # FastAPI route modules
│       ├── services/         # Ingestion and workflow orchestration
│       ├── integrations/     # Prisma, Batch STT, hosted LLM, Timbre adapters
│       ├── prompts/          # Corporate and Student prompts
│       ├── exporters/        # PDF, DOCX, audio export
│       └── schemas/          # Validated request/output models
├── docs/
│   └── architecture.md
├── .env.example
└── requirements.txt
```

## Design rules

- Keep provider-specific HTTP details inside integration adapters.
- Keep corporate/student business rules outside provider adapters.
- Never expose API keys in browser code or commit local `.env` files.
- Preserve source references and distinguish confirmed facts from unknowns.
- Do not claim an integration works until its API contract and end-to-end behavior are tested.
- Use non-confidential sample files for public demos.
