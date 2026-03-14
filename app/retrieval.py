import json
from rank_bm25 import BM25Okapi

with open("data/threaded_emails.json") as f:
    emails = json.load(f)

documents = []
for e in emails:
    text = f"""
    Subject: {e.get('subject_clean','')}
    From: {e.get('from','')}
    To: {e.get('to','')}

    {e.get('body','')}
    """

    documents.append({
        "thread_id": e["thread_id"],
        "message_id": e.get("message_id",""),
        "text": text.strip()
    })

corpus = [doc["text"].lower().split() for doc in documents]

bm25 = BM25Okapi(corpus)


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