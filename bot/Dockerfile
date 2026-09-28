# Образ MAX-бота SkillQuest.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Сначала зависимости — для кэширования слоёв.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Код бота (main.py, api.py, handlers/ и т.д.).
COPY . .

CMD ["python", "main.py"]