import re
import uuid

sessions = {}

# Simple entity extraction patterns (people, dates, amounts, filenames)
RE_DATE = re.compile(
    r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})\b",
    re.I,
)
RE_AMOUNT = re.compile(r"\b(\$?\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:dollars?|USD|million|M|K)?)\b", re.I)
RE_FILENAME = re.compile(r"\b([a-zA-Z0-9_\-]+\.(?:pdf|doc|xls|xlsx|docx|txt|html))\b", re.I)


def _extract_entities(text: str) -> dict:
    if not text:
        return {"people": [], "dates": [], "amounts": [], "filenames": []}
    return {
        "people": [],  # skip NER for now; could add from "X said" or email headers
        "dates": list(dict.fromkeys(RE_DATE.findall(text))),
        "amounts": list(dict.fromkeys(RE_AMOUNT.findall(text))),
        "filenames": list(dict.fromkeys(RE_FILENAME.findall(text))),
    }


def start_session(thread_id: str) -> str:
    session_id = str(uuid.uuid4())
    sessions[session_id] = {
        "thread_id": thread_id,
        "history": [],
        "entities": {"people": [], "dates": [], "amounts": [], "filenames": []},
    }
    return session_id


def update_memory(session_id: str, user: str, answer: str) -> None:
    sessions[session_id]["history"].append({"user": user, "assistant": answer})
    sessions[session_id]["history"] = sessions[session_id]["history"][-5:]

    # Append new entities from this turn (dedupe by keeping recent first)
    for key in ("people", "dates", "amounts", "filenames"):
        new_ones = _extract_entities(user + " " + answer).get(key, [])
        for e in new_ones:
            if e and e not in sessions[session_id]["entities"][key]:
                sessions[session_id]["entities"][key].insert(0, e)
        sessions[session_id]["entities"][key] = sessions[session_id]["entities"][key][:20]


def get_entity_context(session_id: str) -> str:
    """Return a short string of recent entities for query rewrite context."""
    if session_id not in sessions:
        return ""
    ent = sessions[session_id].get("entities", {})
    parts = []
    if ent.get("filenames"):
        parts.append("filenames: " + ", ".join(ent["filenames"][:3]))
    if ent.get("dates"):
        parts.append("dates: " + ", ".join(ent["dates"][:3]))
    if ent.get("amounts"):
        parts.append("amounts: " + ", ".join(ent["amounts"][:3]))
    if not parts:
        return ""
    return " [Context: " + "; ".join(parts) + "]"
