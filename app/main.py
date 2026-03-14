import time
import json
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.retrieval import search
from app.memory import start_session, sessions, update_memory
from app.answer import generate_answer

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://127.0.0.1:5174", "http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
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

def rewrite_query(session_id, query):

    history = sessions[session_id]["history"]

    if not history:
        return query

    last_turn = history[-1]["user"]

    # simple baseline rewrite
    rewritten = last_turn + " " + query

    return rewritten


# -------- API endpoints --------


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/start_session")
def start(req: StartRequest):

    session_id = start_session(req.thread_id)

    return {"session_id": session_id}


@app.post("/ask")
def ask(req: AskRequest):

    start_time = time.time()

    session_id = req.session_id
    user_query = req.text

    if session_id not in sessions:
        raise HTTPException(
            status_code=400,
            detail="Session not found. The server may have restarted. Please start a new session from the thread selector.",
        )

    thread_id = sessions[session_id]["thread_id"]
    trace_id = str(uuid.uuid4())

    try:
        rewritten = rewrite_query(session_id, user_query)
        results = search(
            rewritten,
            None if req.search_outside_thread else thread_id
        )
        answer, citations = generate_answer(user_query, results)
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
            "citations": [],
            "answer": f"Error: {e}",
            "latency": time.time() - start_time,
        }

    latency = time.time() - start_time
    trace = {
        "trace_id": trace_id,
        "query": user_query,
        "rewrite": rewritten,
        "thread_id": thread_id,
        "retrieved": [{"message_id": r[1]["message_id"], "score": r[0]} for r in results],
        "citations": citations,
        "answer": (answer or "No answer was generated. Please try again.").strip(),
        "latency": latency,
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