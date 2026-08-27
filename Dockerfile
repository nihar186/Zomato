FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV INCLUDE_RAW_ATTRIBUTES=false

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY src/ /app/src/
COPY scripts/warm_cache.py /app/scripts/warm_cache.py
RUN PYTHONPATH=. python /app/scripts/warm_cache.py


FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV INCLUDE_RAW_ATTRIBUTES=false

WORKDIR /app

COPY requirements-prod.txt /app/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements-prod.txt

COPY src/ /app/src/
COPY --from=builder /app/data/cache/ /app/data/cache/

EXPOSE 8000

CMD ["sh", "-c", "uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
