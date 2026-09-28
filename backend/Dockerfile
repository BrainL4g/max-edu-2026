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

# По умолчанию база лежит в /app/data (volume из compose.yaml).
ENV DATABASE_URL=sqlite:////app/data/skillquest.db

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]