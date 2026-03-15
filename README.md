# Email Thread RAG

Chat over email threads with RAG (retrieval-augmented generation). React UI + FastAPI backend. Answers are grounded in the selected thread with message-level citations.

## Setup and run

### With Docker (one command)

From the project root, with a `.env` containing `GEMINI_API_KEY` and optionally `GEMINI_MODEL`:

```bash
docker compose up --build
```

Then open **http://localhost:8000** in your browser. The container runs the **indexer** (`ingest.py`) on startup, then the API and UI. Ensure `data/threaded_emails.json` exists in the image (e.g. run `python ingest.py` locally first with `data/emails.csv`, or copy a pre-built `data/` into the build context).

### Run locally

1. **Index (once):** From CSV (e.g. [Enron](https://www.kaggle.com/datasets/wcukierski/enron-email-dataset)) or from a directory of `.eml` files:
   ```bash
   python ingest.py
   ```
   Or with a directory of `.eml` files: `python ingest.py --eml-dir path/to/emails`. This writes `data/threaded_emails.json`. If you already have that file (e.g. from the dataset-cleaning notebook), you can skip this.

2. **Backend:** `uvicorn app.main:app --reload --port 8000`
3. **Frontend:** `cd ui && npm install && npm run dev`
4. **Environment:** `.env` with `GEMINI_API_KEY` (and optionally `GEMINI_MODEL`).

## Dataset

See **[DATASET.md](DATASET.md)** for source, how the slice was selected, counts, preprocessing, and license.

## Retrieval

- **Baseline:** BM25 (keyword) only, implemented with `rank_bm25.BM25Okapi`. Retrieval is **thread-scoped** by default: when a session is tied to a `thread_id`, only chunks from that thread are searched. Optional **search outside thread** (UI toggle or `search_outside_thread=true`) allows global search.
- **Index:** Emails are stored as one chunk per message (`data/threaded_emails.json`) with `doc_id`, `thread_id`, `message_id`. Attachment chunking (PDF/DOCX/TXT/HTML, with `page_no` for PDFs) is optional via `ingest.py --attachments-dir`.

## Design choices and limitations

- **Sessions:** One session per thread; conversation history is the last few turns (no rolling summary). Entity notes (people, dates, amounts, filenames) are extracted from the conversation and used in query rewrite. Corrections (e.g. “no, I meant the Q3 forecast”) are detected so only the new intent is used for retrieval.
- **Answering:** Gemini is used to generate answers from retrieved excerpts. Citations are inline `[msg: <message_id>]`; attachment citations `[msg: <id>, page: <n>]` apply when attachment chunks are added.
- **Free path:** The app runs with the **Gemini API free tier** (set `GEMINI_API_KEY`). No paid resources are required for evaluation.

## How to test

1. Start a session by choosing a thread and clicking “Start Session”.
2. Ask a question about that thread (e.g. “What was discussed about the forecast?”). Check that the answer cites message IDs from the debug panel.
3. Toggle “Search outside thread” and ask again; retrieval may include messages from other threads.
4. Inspect `runs/<timestamp>/trace.jsonl` for each turn (query, rewrite, retrieved, citations, latency).

## Sample questions and expected citations

See **[SAMPLES.md](SAMPLES.md)** for 5–10 example questions on a chosen thread with expected message (and optional page) citations.

## API

- `POST /start_session` — body `{ "thread_id": "T-001" }` → `{ "session_id": "..." }`
- `POST /ask` — body `{ "session_id": "...", "text": "...", "search_outside_thread": false }` → `{ "answer", "citations", "rewrite", "retrieved", "trace_id", "latency", ... }`
- `POST /switch_thread` — body `{ "thread_id": "..." }`
- `POST /reset_session`
- `GET /threads` — returns list of `{ "thread_id", "label" }` for the UI dropdown. When the user asks for a timeline (e.g. "Show timeline" or "Who said what when?"), the `/ask` response returns a chronological timeline with citations.
