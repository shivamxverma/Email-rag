import json
import os
import re
import time
from pathlib import Path

# Load .env so GEMINI_* are available when this module is imported
_env_loaded = False
def _ensure_dotenv():
    global _env_loaded
    if not _env_loaded:
        try:
            from dotenv import load_dotenv
            load_dotenv(Path(__file__).resolve().parents[1] / ".env")
        except Exception:
            pass
        _env_loaded = True


def _get_client():
    _ensure_dotenv()
    from google import genai
    api_key = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip().strip('"')
    if not api_key:
        raise RuntimeError(
            "Set GEMINI_API_KEY or GOOGLE_API_KEY in the environment (e.g. in .env) to use Gemini."
        )
    return genai.Client(api_key=api_key)


# Deprecated models return 404; use this fallback if user still has one in .env
_SUPPORTED_DEFAULT = "gemini-2.0-flash"

def _get_model():
    _ensure_dotenv()
    raw = (os.environ.get("GEMINI_MODEL") or _SUPPORTED_DEFAULT).strip().strip('"')
    model = raw or _SUPPORTED_DEFAULT
    # Redirect deprecated 1.5-* models to a supported one
    if "gemini-1.5" in model:
        model = _SUPPORTED_DEFAULT
    return model


def _build_context(results):
    """Turn retrieval results into a single context string with message IDs for citations."""
    parts = []
    for score, doc in results:
        mid = doc.get("message_id", "")
        text = (doc.get("text") or "")[:4000]
        parts.append(f"[msg: {mid}]\n{text}")
    return "\n\n---\n\n".join(parts)


def _extract_citations(text):
    """Extract [msg: ...] citations from model output."""
    return list(dict.fromkeys(re.findall(r"\[msg:\s*[^\]]+\]", text)))


# Strict response format: JSON with "answer" (clean text) and "citations"
STRICT_FORMAT_INSTRUCTIONS = """
You must respond with exactly one JSON object (no other text, no markdown fences). Use this shape:
{"answer": "<your answer text>", "citations": ["[msg: <id>]", ...]}

Rules for "answer":
- Use ONLY the email excerpts above. Do not invent information.
- Write in a clean, readable format: short paragraphs (2–4 sentences), clear sentences, proper punctuation.
- For lists or multiple points, use line breaks between items or short bullet-like phrases.
- When referring to a specific message, add the citation at the end of that sentence: [msg: <message_id>]. The message_id is at the start of each excerpt above.
- Be concise and direct. No preamble like "Based on the emails..."; start with the answer.

Rules for "citations":
- Array of strings. List every [msg: <message_id>] you used in the answer, e.g. ["[msg: abc123]", "[msg: def456]"].
- If no message is cited, use "citations": [].
"""


def generate_answer(query, results, model=None):
    """
    Use Gemini to answer the user query from the retrieved excerpts.
    Returns (answer_text, list of citation strings like "[msg: ...]") in a strict format.
    """
    if not results:
        return "I couldn't find any relevant messages to answer from.", []

    context = _build_context(results)
    model_id = (model or _get_model()).strip().strip('"') or _SUPPORTED_DEFAULT
    if "gemini-1.5" in model_id:
        model_id = _SUPPORTED_DEFAULT

    prompt = f"""You are answering questions about an email thread. Use ONLY the following email excerpts. Do not make up information.

## Email excerpts

{context}

## Question

{query}

## Response format

{STRICT_FORMAT_INSTRUCTIONS}

Respond with only the JSON object:"""

    max_attempts = 3
    last_error = None

    for attempt in range(max_attempts):
        try:
            client = _get_client()
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
            )
            raw = (response.text or "").strip()
            last_error = None
            break
        except Exception as e:
            last_error = e
            err_str = str(e)
            is_429 = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "quota" in err_str.lower()
            if is_429 and attempt < max_attempts - 1:
                # Parse "Please retry in 56.366478021s." or use 60s default
                match = re.search(r"retry in ([\d.]+)s", err_str, re.I)
                wait = float(match.group(1)) if match else 60.0
                wait = min(wait, 120)  # cap at 2 minutes
                time.sleep(wait)
            else:
                return f"Error calling Gemini: {e}", []
    else:
        if last_error:
            return f"Error calling Gemini: {last_error}", []
        return "No answer generated.", []

    if not raw:
        return "No answer generated.", []

    # Parse strict JSON response
    try:
        # Remove optional markdown code block if present
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```\s*$", "", raw)
        data = json.loads(raw)
        answer = (data.get("answer") or "").strip()
        citations = data.get("citations")
        if not isinstance(citations, list):
            citations = []
        citations = [str(c).strip() for c in citations if c]
        return (answer or "No answer generated. Please try again."), citations
    except (json.JSONDecodeError, TypeError):
        # Fallback: treat whole response as answer and extract citations
        citations = _extract_citations(raw)
        return (raw or "No answer generated. Please try again."), citations
