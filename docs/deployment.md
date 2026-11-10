# MOMENT AI deployment

## Deploy with Render Blueprint

The repository includes `render.yaml`, which provisions two services:
- `moment-ai-api`: Python 3.11 FastAPI backend, with `/health` health checks.
- `moment-ai-web`: React/Vite static frontend, configured to call the backend URL.

The Blueprint explicitly configures the Gnani Prisma, Batch STT, and Timbre endpoints and the Groq chat-completions endpoint. Automatic deploys are enabled for pushes to the connected branch.

### Deploy steps

1. Push the latest `main` branch to GitHub.
2. Sign in at [Render](https://dashboard.render.com/).
3. Select **New + → Blueprint**.
4. Connect the GitHub repository `maheka42/moment-ai` and select the `main` branch.
5. Review the two services from `render.yaml`.
6. Enter the two secret values when Render prompts:
   - `GNANI_API_KEY_ID`: your Gnani API Key ID.
   - `LLM_API_KEY`: your Groq API key.
7. Apply the Blueprint and wait for both services to finish deploying.

Do not put API keys in GitHub, source files, screenshots, or chat messages. Enter them only in Render's secret environment-variable fields.

### Deployed URLs

- Frontend: `https://moment-ai-web.onrender.com`
- Backend health: `https://moment-ai-api.onrender.com/health`
- Backend API docs: `https://moment-ai-api.onrender.com/docs`

If either generated service URL differs because the name is unavailable, update `CORS_ORIGINS` on the backend and `VITE_API_BASE_URL` on the frontend to the actual URLs, then redeploy both services.

### Verify after deployment

1. Open the backend health URL. Confirm `status` is `ok` and `integrations.llm`, `integrations.prisma_rest`, `integrations.batch_stt`, and `integrations.timbre` are `true`.
2. Open the frontend and test text input in both Corporate and Student modes.
3. Test PDF and DOCX exports.
4. Test a small audio upload/transcription with Gnani credentials.
5. Test MP3 narration separately.

The health endpoint confirms that configuration values are present; it does not validate provider credentials or provider availability. A successful text-generation request is the practical check for Groq connectivity.

### Known provider limitation

A local Timbre v2.5 narration test previously reached the Gnani API but received HTTP 503 with a generic provider-side technical-difficulties message. Deploying to Render will not fix a provider-side 503. If narration still returns 503 after deployment, check the Gnani dashboard for Timbre access/credits and retry later or contact Gnani support. The rest of the app can be deployed and tested independently.

### Deployment limitations

- Render free services may sleep when idle and take time to wake.
- Real provider connectivity cannot be proven by CI because API credentials are intentionally not stored in the repository.
- The corporate validator is deliberately conservative: a decision, action item, question, or risk without an exact source excerpt is omitted.
- If the model returns invalid JSON, generation fails with a clear 502 rather than showing unvalidated minutes.