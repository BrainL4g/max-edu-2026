FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build
COPY requirements.txt requirements.txt
RUN pip install --prefix=/install -r requirements.txt

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=production

WORKDIR /app

COPY --from=builder /install /usr/local

COPY alembic.ini ./backend/alembic.ini
COPY alembic ./backend/alembic
COPY app ./backend/app
COPY entrypoint.sh ./backend/entrypoint.sh

RUN sed -i 's/\r$//' /app/backend/entrypoint.sh && \
    chmod +x /app/backend/entrypoint.sh && \
    useradd --create-home --uid 10001 appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app/data /app/backend

# Сертификаты НУЦ Минцифры (root + sub) — нужны для TLS к api.giga.chat и oauth.
# Путь задаётся образом, а не через compose/.env: хостовый GIGACHAT_CA_BUNDLE
# действует только при запуске вне Docker.
COPY gigachat/russian_trusted_ca.pem /etc/ssl/gigachat/russian_trusted_ca.pem
ENV GIGACHAT_CA_BUNDLE=/etc/ssl/gigachat/russian_trusted_ca.pem

# По умолчанию база лежит в /app/data (volume из compose.yaml).
ENV DATABASE_URL=sqlite:////app/data/skillquest.db

USER appuser
EXPOSE 8000

CMD ["sh", "/app/backend/entrypoint.sh"]
