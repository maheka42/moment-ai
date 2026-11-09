# MOMENT AI deployment

## Deploy with Render Blueprint

The repository includes a Render Blueprint in render.yaml. It defines:
- A Python 3.11 FastAPI service named moment-ai-api.
- A static React/Vite frontend named moment-ai-web.
- A backend health check at /health.
- Frontend API configuration and backend CORS configuration for the generated Render URLs.

### Steps

1. Push the latest main branch to GitHub.
2. In Render, choose New → Blueprint and select maheka42/moment-ai.
3. Review the two services and deploy the Blueprint.
4. When prompted, enter the private values for GNANI_API_KEY_ID and LLM_API_KEY. Do not put either key in GitHub.
5. Wait until both services are live.

### Verify after deployment

- Open https://moment-ai-api.onrender.com/health. Confirm the service reports status: ok and that the required llm integration is true.
- Open https://moment-ai-web.onrender.com and generate a corporate and a student output.
- Test PDF and DOCX export.
- Test audio upload/transcription and MP3 narration with real Gnani credentials.
- Check the Render service logs if a provider returns an error.

### Required secrets and configuration

| Variable | Purpose |
|---|---|
| GNANI_API_KEY_ID | Gnani Prisma and Timbre API access |
| LLM_API_KEY | Groq API key |
| LLM_API_URL | Defaults to the Groq chat-completions endpoint in the Blueprint |
| LLM_MODEL | Defaults to openai/gpt-oss-120b |
| CORS_ORIGINS | Must include the exact deployed frontend origin |
| VITE_API_BASE_URL | Must point to the deployed FastAPI service |

If you use custom domains, update CORS_ORIGINS and VITE_API_BASE_URL to match them, then redeploy the frontend so the Vite build receives the correct API URL.

## Deployment limitations

- Render free services may sleep when idle and take time to wake.
- Real provider connectivity cannot be proven by CI because API credentials are intentionally not stored in the repository.
- The /health endpoint verifies configuration presence, not whether provider credentials are accepted. Run the live smoke tests above after deployment.
- The corporate validator is deliberately conservative: a decision, action item, question, or risk without an exact source excerpt is omitted. If the model returns invalid JSON, generation fails with a clear 502 rather than showing unvalidated minutes.
