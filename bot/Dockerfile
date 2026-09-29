# Production-ready образ MAX-бота SkillQuest: multi-stage + non-root.
# ---- Stage 1: установка зависимостей ----
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build
COPY requirements.txt requirements.txt
RUN pip install --prefix=/install -r requirements.txt

# ---- Stage 2: рантайм ----
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY --from=builder /install /usr/local
COPY . .

RUN useradd --create-home --uid 10001 appuser && \
    chown -R appuser:appuser /app

USER appuser
CMD ["python", "main.py"]