import json
from pathlib import Path
from rank_bm25 import BM25Okapi

with open("data/threaded_emails.json") as f:
    emails = json.load(f)

documents = []
for i, e in enumerate(emails):
    text = f"""
    Subject: {e.get('subject_clean','')}
    From: {e.get('from','')}
    To: {e.get('to','')}
    Cc: {e.get('cc','')}

    {e.get('body','')}
    """
    documents.append({
        "doc_id": e.get("doc_id", f"em_{i}"),
        "thread_id": e["thread_id"],
        "message_id": e.get("message_id", ""),
        "text": text.strip(),
    })

# Optional: attachment chunks (doc_id, message_id, page_no, text, thread_id)
_attachment_path = Path("data/attachment_chunks.json")
if _attachment_path.exists():
    try:
        with open(_attachment_path) as af:
            for ch in json.load(af):
                documents.append({
                    "doc_id": ch.get("doc_id", ""),
                    "thread_id": ch.get("thread_id") or "",
                    "message_id": ch.get("message_id", ""),
                    "text": (ch.get("text") or "").strip(),
                    "page_no": ch.get("page_no"),
                })
    except Exception:
        pass

corpus = [doc["text"].lower().split() for doc in documents]

bm25 = BM25Okapi(corpus)

# Thread list for API: thread_id -> label (first subject_clean in that thread)
_thread_labels = {}
for e in emails:
    t = e.get("thread_id", "")
    if t and t not in _thread_labels:
        _thread_labels[t] = (e.get("subject_clean") or e.get("subject") or t)[:80]


def list_threads():
    """Return list of {thread_id, label} for ingested threads."""
    return [{"thread_id": tid, "label": _thread_labels.get(tid, tid)} for tid in sorted(_thread_labels)]


def get_thread_timeline(thread_id: str):
    """Return timeline for thread: who said what, when, with message_id for citations. Sorted by date."""
    out = []
    for e in emails:
        if e.get("thread_id") != thread_id:
            continue
        date = (e.get("date") or "").strip()
        from_ = (e.get("from") or e.get("x_from") or "").strip()
        to = (e.get("to") or e.get("x_to") or "").strip()
        mid = e.get("message_id", "")
        subj = (e.get("subject_clean") or e.get("subject") or "").strip()
        body = (e.get("body") or "").strip()[:200]
        out.append({
            "date": date,
            "from": from_,
            "to": to,
            "message_id": mid,
            "subject": subj,
            "body_snippet": body,
        })
    # Sort by date string (best-effort; RFC-style dates sort lexicographically for ISO-like)
    out.sort(key=lambda x: (x["date"], x["message_id"]))
    return out


def search(query, thread_id=None, top_k=5):
    if not documents:
        return []

    query_tokens = query.lower().split()
    scores = bm25.get_scores(query_tokens)

    results = []

    for i, score in enumerate(scores):

        doc = documents[i]

        if thread_id and doc["thread_id"] != thread_id:
            continue

        results.append((score, doc))

    results.sort(key=lambda x: x[0], reverse=True)

    return results[:top_k]