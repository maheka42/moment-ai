# MOMENT AI — Architecture

## Architecture decision

Start with a **modular monolith**: one React web client and one FastAPI backend, organized into clear internal modules. Do not split into microservices for the MVP.

## Logical layers

1. **Frontend** — React + TypeScript + Vite; user interface and upload interactions.
2. **API layer** — FastAPI routes; request validation and response handling.
3. **Ingestion layer** — PDF, text, and audio input normalization; preserve page/timestamp provenance.
4. **AI integration layer** — isolated adapters for Gnani Prisma (STT), Evon (reasoning), and Timbre (TTS).
5. **Workflow/business layer** — corporate meeting minutes and student study-notes workflows.
6. **Export layer** — PDF, DOCX, and audio output.
7. **Data layer** — Firebase/Firestore is planned for user data and document metadata; storage design will be finalized before persistence is implemented.
8. **Security/configuration layer** — environment-based secrets, upload limits, CORS, validation, access control, and retention.

## Request flows

### Corporate
Recording → Prisma transcription → evidence-grounded meeting workflow using Evon → reviewable MoM → PDF/DOCX export and optional Timbre narration.

### Student
Lecture recording/PDF/text → extraction or Prisma transcription → evidence-grounded study workflow using Evon → reviewable notes → PDF/DOCX export and optional Timbre narration.

## Proposed repository layout

```text
moment-ai/
├── frontend/                 # React + TypeScript + Vite
│   └── src/
├── backend/
│   └── app/
│       ├── api/              # FastAPI route modules
│       ├── services/         # Ingestion and workflow orchestration
│       ├── integrations/     # Prisma, Evon, Timbre adapters
│       ├── prompts/          # Corporate and Student prompts
│       ├── exporters/        # PDF, DOCX, audio export
│       └── schemas/          # Validated request/output models
├── docs/
│   └── architecture.md
├── .env.example
└── requirements.txt
```

## Design rules

- Keep provider-specific HTTP details inside `integrations/`.
- Keep corporate/student business rules outside provider adapters.
- Never expose API keys in browser code.
- Preserve source references and distinguish confirmed facts from unknowns.
- Do not claim an integration works until its API contract and end-to-end behavior are tested.
- Use non-confidential sample files for public demos.
