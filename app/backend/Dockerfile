# Backend image. Build from the repo root, because the service reads app/contract and shared/:
#   docker build -f app/backend/Dockerfile -t screener .
# Railway uses this through app/backend/railway.json (set the service's config file path to it).
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /srv

COPY app/backend/requirements.txt app/backend/requirements.txt
RUN pip install -r app/backend/requirements.txt

# The same layout as the repo, so the service finds the contract and artefacts at their usual paths.
COPY app/backend/screener app/backend/screener
COPY app/contract app/contract
COPY shared shared

RUN useradd --create-home --uid 10001 app
USER app

ENV ENV=prod PORT=8000
EXPOSE 8000
# One process: jobs, memos and push subscriptions live in memory (nothing is stored after the session).
CMD ["sh", "-c", "exec uvicorn screener.main:app --app-dir app/backend --host 0.0.0.0 --port \"$PORT\" --proxy-headers --forwarded-allow-ips='*'"]
