#!/bin/sh
# Run indexer if possible, then start API + UI.
set -e
python ingest.py 2>/dev/null || true
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
