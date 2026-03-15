import time
import json
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.retrieval import search, list_threads, get_thread_timeline
from app.memory import start_session, sessions, update_memory, get_entity_context
from app.answer import generate_answer

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://127.0.0.1:5174", "http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",  # any localhost port (e.g. Vite 5175, 5176)
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# -------- request schemas --------

class StartRequest(BaseModel):
    thread_id: str


class AskRequest(BaseModel):
    session_id: str
    text: str
    search_outside_thread: bool = False


# -------- trace logging --------

run_id = time.strftime("%Y%m%d-%H%M%S")
run_dir = Path("runs") / run_id
run_dir.mkdir(parents=True, exist_ok=True)

trace_file = run_dir / "trace.jsonl"


def log_trace(data):
    with open(trace_file, "a") as f:
        f.write(json.dumps(data) + "\n")


# -------- query rewrite --------

# Phrases that indicate the user is correcting or clarifying the previous question
CORRECTION_PHRASES = (
    "no,", "no ", "actually", "i meant", "i mean", "sorry,", "correction:",
    "correction ", "wait,", "rather,", "instead ", "not that",
)


def rewrite_query(session_id, query):
    """Rewrite using last turn and entity notes so 'that', 'it', 'the draft' resolve better.
    When the user corrects (e.g. 'no, I meant the Q3 forecast'), use only the current message + context."""
    history = sessions[session_id]["history"]
    entity_ctx = get_entity_context(session_id)

    # Resolve pronouns/ellipsis: if query references "that", "it", "the draft", "the attachment", add context
    need_context = any(
        phrase in query.lower()
        for phrase in ("that", " it ", "the draft", "the attachment", "the file", "the approval", "the version")
    )
    if need_context and entity_ctx:
        query = query + " " + entity_ctx

    # Correction: user is replacing/clarifying the previous question — don't prepend last turn
    q_lower = query.lower().strip()
    is_correction = any(q_lower.startswith(p.strip()) for p in CORRECTION_PHRASES)
    if is_correction:
        rewritten = query
    elif history:
        last_turn = history[-1]["user"]
        rewritten = last_turn + " " + query
    else:
        rewritten = query
    return rewritten


# -------- API endpoints --------


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/threads")
def threads():
    """Return list of thread_id and label for the thread selector (from ingested index)."""
    try:
        return {"threads": list_threads()}
    except Exception:
        return {"threads": []}


@app.post("/start_session")
def start(req: StartRequest):

    session_id = start_session(req.thread_id)

    return {"session_id": session_id}


@app.post("/ask")
def ask(req: AskRequest, search_outside_thread: bool = False):

    start_time = time.time()

    session_id = req.session_id
    user_query = req.text
    # Support both body and query param (?search_outside_thread=true)
    search_outside = req.search_outside_thread or search_outside_thread

    if session_id not in sessions:
        raise HTTPException(
            status_code=400,
            detail="Session not found. The server may have restarted. Please start a new session from the thread selector.",
        )

    thread_id = sessions[session_id]["thread_id"]
    trace_id = str(uuid.uuid4())

    # Timeline: if user asks for "timeline" / "who said what when", return timeline with citations
    q_lower = user_query.lower().strip()
    if any(phrase in q_lower for phrase in ("timeline", "who said what", "who wrote what", "when did who", "chronological order", "order of messages")):
        try:
            timeline = get_thread_timeline(thread_id)
            lines = []
            citations = []
            for row in timeline:
                mid = row.get("message_id", "")
                if mid:
                    citations.append(f"[msg: {mid}]")
                lines.append(
                    f"{row.get('date', '')} | From: {row.get('from', '')} | To: {row.get('to', '')} | "
                    f"[msg: {mid}]\n  Subject: {row.get('subject', '')}\n  {row.get('body_snippet', '')[:150]}..."
                )
            answer = "Timeline for this thread (who said what, when):\n\n" + "\n\n".join(lines) if lines else "No messages found in this thread."
            update_memory(session_id, user_query, answer)
            latency = time.time() - start_time
            trace = {
                "trace_id": trace_id,
                "query": user_query,
                "rewrite": user_query,
                "thread_id": thread_id,
                "retrieved": [],
                "retrieved_used": [],
                "citations": citations,
                "answer": answer,
                "latency": latency,
                "token_counts": {},
            }
            try:
                log_trace(trace)
            except Exception:
                pass
            return trace
        except Exception as e:
            pass  # fall through to normal RAG

    try:
        rewritten = rewrite_query(session_id, user_query)
        results = search(
            rewritten,
            None if search_outside else thread_id
        )
        answer, citations, usage = generate_answer(user_query, results)
        if not (answer and str(answer).strip()):
            answer = "No answer was generated. Please try again or rephrase your question."
        update_memory(session_id, user_query, answer)
    except Exception as e:
        return {
            "trace_id": trace_id,
            "query": user_query,
            "rewrite": "",
            "thread_id": thread_id,
            "retrieved": [],
            "retrieved_used": [],
            "citations": [],
            "answer": f"Error: {e}",
            "latency": time.time() - start_time,
            "token_counts": {},
        }

    # Which retrieved items appear in citations (message_id, optional page)
    retrieved_used = []
    for _, doc in results:
        mid = doc.get("message_id", "")
        page = doc.get("page_no")
        for c in citations:
            if mid and mid in c:
                if page is not None and f"page: {page}" in c:
                    retrieved_used.append({"message_id": mid, "page_no": page})
                elif page is None:
                    retrieved_used.append({"message_id": mid, "page_no": page})
                break

    latency = time.time() - start_time
    trace = {
        "trace_id": trace_id,
        "query": user_query,
        "rewrite": rewritten,
        "thread_id": thread_id,
        "retrieved": [{"message_id": r[1]["message_id"], "score": r[0], **({"page_no": r[1]["page_no"]} if r[1].get("page_no") is not None else {})} for r in results],
        "retrieved_used": retrieved_used,
        "citations": citations,
        "answer": (answer or "No answer was generated. Please try again.").strip(),
        "latency": latency,
        "token_counts": usage,
    }
    try:
        log_trace(trace)
    except Exception:
        pass
    return trace


@app.post("/switch_thread")
def switch_thread(req: StartRequest):

    session_id = start_session(req.thread_id)

    return {"session_id": session_id}


@app.post("/reset_session")
def reset():

    sessions.clear()

    return {"status": "reset"}


# Serve built frontend (when running in Docker; static/ is populated at build time)
if Path("static").exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory="static", html=True), name="static")