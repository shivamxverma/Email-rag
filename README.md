# Email Thread RAG

Chat over email threads with RAG (Gemini). React UI + FastAPI backend.

## Run with Docker (one command)

From the project root, with a `.env` containing `GEMINI_API_KEY` and optionally `GEMINI_MODEL`:

```bash
docker compose up --build
```

Then open **http://localhost:8000** in your browser. The UI and API run in one container.

## Run locally

1. Backend: `uvicorn app.main:app --reload --port 8000`
2. Frontend: `cd ui && npm install && npm run dev`
3. Ensure `.env` has `GEMINI_API_KEY` (and optionally `GEMINI_MODEL`).
