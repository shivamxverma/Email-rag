# ---- Frontend ----
FROM node:20-alpine AS frontend
WORKDIR /build

COPY ui/package.json ui/package-lock.json* ./
RUN npm ci

COPY ui/ ./
# Same-origin API when served from backend (empty = use relative URLs)
ENV VITE_API_BASE=
RUN npm run build

# ---- Backend ----
FROM python:3.12-slim
WORKDIR /app

# Data and app
COPY requirements.txt ./
COPY app/ ./app/
COPY data/ ./data/

RUN pip install --no-cache-dir -r requirements.txt

# Built frontend → static (FastAPI will serve this at /)
COPY --from=frontend /build/dist ./static

# Optional: create runs dir for trace logs
RUN mkdir -p runs

EXPOSE 8000

# Env: pass GEMINI_API_KEY, GEMINI_MODEL via --env-file .env or -e
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
