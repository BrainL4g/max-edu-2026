# Production-ready образ бэкенда SkillQuest.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=production

WORKDIR /app

# Сначала зависимости — для кэширования слоёв.
COPY requirements.txt ./backend/requirements.txt
RUN pip install --upgrade pip && pip install -r backend/requirements.txt

# Код приложения, миграции и конфигурация (пакет backend/ внутри /app).
COPY . ./backend

# Сертификаты НУЦ Минцифры (root + sub) — нужны для TLS к api.giga.chat и oauth.
# Путь задаётся образом, а не через compose/.env: хостовый GIGACHAT_CA_BUNDLE
# действует только при запуске вне Docker.
COPY gigachat/russian_trusted_ca.pem /etc/ssl/gigachat/russian_trusted_ca.pem
ENV GIGACHAT_CA_BUNDLE=/etc/ssl/gigachat/russian_trusted_ca.pem

# По умолчанию база лежит в /app/data (volume из compose.yaml).
ENV DATABASE_URL=sqlite:////app/data/skillquest.db

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]