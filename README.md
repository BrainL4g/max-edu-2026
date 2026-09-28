# SkillQuest 🎮

> Игровое мини-приложение для студентов: диагностика навыков → игровые миссии →
> прокачка Skill Map → рекомендации курсов и стажировок → анализ резюме.

---

## Содержание

1. [Что такое SkillQuest](#1-что-такое-skillquest)
2. [Проблема](#2-проблема)
3. [Основной пользовательский сценарий](#3-основной-пользовательский-сценарий)
4. [Возможности](#4-возможности)
5. [Архитектура](#5-архитектура)
6. [Зависимости](#6-зависимости)
7. [Окружение и переменные](#7-окружение-и-переменные)
8. [Данные](#8-данные)
9. [Интеграции](#9-интеграции)
10. [Установка](#10-установка)
11. [Docker запуск](#11-docker-запуск)
12. [Запуск тестов](#12-запуск-тестов)
13. [Пошаговая проверка сценария](#13-пошаговая-проверка-сценария)
14. [Известные ограничения](#14-известные-ограничения)

---

## 1. Что такое SkillQuest

**SkillQuest** — игровое приложение, которое помогает студентам:

- понять свой текущий уровень навыков (Skill Map);
- прокачивать навыки через короткие игровые задания-миссии;
- получать персональные рекомендации курсов и стажировок;
- проверять и улучшать резюме.

Backend реализован на **Python + FastAPI + SQLAlchemy + SQLite**, разворачивается
в **Docker**. Весь функционал доступен через HTTP API
(см. [пошаговую проверку](#13-пошаговая-проверка-сценария)).

## 2. Проблема

Студенты и junior-специалисты часто не знают:

- какие навыки им нужно прокачать, чтобы попасть на стажировку;
- какие курсы реально закрывают пробелы в знаниях;
- как выглядит их Skill Map относительно требований работодателей;
- почему резюме «не взлетает» у HR.

SkillQuest превращает этот процесс в игру: диагностика → миссии → XP →
рекомендации → анализ резюме.

## 3. Основной пользовательский сценарий

```text
Студент
   ↓
Первичная диагностика (ответы на вопросы)
   ↓
Начальный Skill Map
   ↓
Игровые миссии (задания по навыкам)
   ↓
Прокачка навыков (опыт → уровни)
   ↓
Рекомендации курсов и стажировок
   ↓
Анализ резюме + советы по доработке
```

## 4. Возможности

- 🧠 **Диагностика** — первичная оценка навыков по категориям.
- 🎮 **Миссии** — игровые задания с вариантами ответов, XP и уровнями.
- 📊 **Skill Map** — уровни и прогресс по каждому навыку.
- 📚 **Курсы** — список, поиск, фильтрация, рекомендации по пробелам.
- 💼 **Стажировки** — список, фильтрация, рекомендации по направлению и навыкам.
- 📄 **Резюме** — загрузка (текст/файл), анализ, отчёт с проблемами и советами.
- 🏷️ **Фильтрация** курсов: `skill`, `category`, `level`, `price`, `format`, `platform`.
- 🏷️ **Фильтрация** стажировок: `direction`, `skills`, `level`, `city`, `remote`, `format`.

## 5. Архитектура

```text
                    User
                      │
          ┌───────────┼───────────┐
          ↓           ↓           ↓
       Missions     Resume      Profile
          ↓           ↓
       Skills      Analysis
          │           │
          └──────┬────┘
                 ↓
           Skill Map
                 ↓
        Recommendation Service
             ↙         ↘
         Courses     Internships
```

Слои backend:

| Слой | Назначение | Путь |
|------|------------|------|
| API (маршруты) | HTTP-эндпоинты, валидация request/response | `backend/app/api/` |
| Services | Бизнес-логика: диагностика, миссии, навыки, рекомендации, анализ резюме | `backend/app/services/` |
| Repositories | Доступ к данным (SQLite), изоляция от SQL | `backend/app/repositories/` |
| Domain | ORM-сущности (таблицы БД) | `backend/app/domain/` |
| Schemas | Pydantic-схемы API | `backend/app/schemas/` |
| Core | Конфигурация и исключения | `backend/app/core/` |
| Database | Engine, сессия | `backend/app/database/` |
| Alembic | Миграции схемы | `backend/alembic/` |

**Стек:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, SQLite,
pytest, httpx, Docker.

## 6. Зависимости

Основные (задекларированы в `backend/pyproject.toml` и `backend/requirements.txt`):

- `fastapi` — веб-фреймворк;
- `uvicorn[standard]` — ASGI-сервер;
- `pydantic` / `pydantic-settings` — валидация и конфигурация;
- `SQLAlchemy` — ORM;
- `alembic` — миграции;
- `python-multipart` — загрузка файлов (резюме).

Dev:

- `pytest`, `pytest-cov`, `httpx` (TestClient), `ruff`.

## 7. Окружение и переменные

Шаблон — `.env.example` в корне. Скопируйте в `.env` (корень репозитория
или `backend/`, приложение найдёт оба места) и заполните:

```env
APP_NAME=SkillQuest
APP_ENV=development
DATABASE_URL=sqlite:///./skillquest.db
```

| Переменная | Значение | По умолчанию |
|-----------|----------|--------------|
| `APP_NAME` | Название приложения | `SkillQuest` |
| `APP_ENV` | `development` / `testing` / `production` | `development` |
| `DATABASE_URL` | URL SQLite (или другой БД через SQLAlchemy) | `sqlite:///./skillquest.db` |
| `AUTO_CREATE_TABLES` | Создавать таблицы при старте (прототип) | `true` |
| `SEED_ON_STARTUP` | Наполнять базу демо-данными при старте | `true` |
| `CORS_ORIGINS` | Разрешённые origins через запятую | `*` |

> ⚠️ Рабочие токены в Git не хранятся: `.env` в `.gitignore`, в примере — только шаблон.

## 8. Данные

**БД SQLite.** Основные таблицы:

```text
users             profiles, направление, цель
skills            каталог навыков (имя, категория, описание)
user_skills       уровень и опыт пользователя в навыке (Skill Map)
missions          игровые задания (навык, сложность, сценарий, XP)
mission_options   варианты ответов (в т.ч. правильный)
attempts          попытки пользователя (ответ, верно/нет, XP)
courses           курсы (платформа, уровень, категория, цена, формат)
course_skills     связь курс → навыки
internships       стажировки (компания, город, удалёнка, формат, направление)
internship_skills связь стажировка → навыки
resumes           резюме пользователя (текст/файл)
resume_analysis   результат анализа (JSON)
```

Связи:

```text
users ── user_skills ── skills
users ── attempts ── missions
users ── resumes ── resume_analysis
courses ── course_skills ── skills
internships ── internship_skills ── skills
```

**Демо-данные.** При `SEED_ON_STARTUP=true` база наполняется 16 навыками,
18 миссиями, 14 курсами и 8 стажировками. Повторный запуск идемпотентен.
Ручной запуск (из корня): `python -m backend.app.seed`.

**Миграции.** Схема управляется Alembic (`backend/alembic/`):
`001_initial_schema.py` (основные таблицы), `002_add_resume_analysis.py`
(резюме и анализ). Применение (из корня):
`alembic -c backend/alembic.ini upgrade head`.

## 9. Интеграции

- **CORS** — настроен (`CORS_ORIGINS`), чтобы фронтенд (React) мог обращаться
  к API из браузера.
- **Swagger UI** — встроенная документация API на `/docs`.
- **OpenAPI** — спецификация на `/openapi.json` (для генерации клиентов).

### Использование API из кода (Python)

Роутеры вынесены в пакет `backend.app.api.routes` и подключаются единым
`api_router` (см. `backend/app/api/router.py`). Пример:

```python
from backend.app.api.routes import courses, internships, missions, resumes, skills, users
from fastapi import FastAPI

app = FastAPI()
for module in (users, skills, missions, courses, internships, resumes):
    app.include_router(module.router)
```

Каждый модуль экспонирует объект `fastapi.APIRouter` в `module.router`,
поэтому роутеры можно подключать выборочно.

## 10. Установка

```bash
# 1. Клонировать репозиторий
git clone <repo-url> && cd max-edu-2026

# 2. Создать окружение и установить зависимости
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # Linux/macOS
pip install -r requirements.txt
pip install pytest httpx pytest-cov ruff

# 3. Настроить окружение (корень репозитория)
copy ..\.env.example ..\.env
cd ..

# 4. Запустить API (из корня репозитория)
uvicorn backend.app.main:app --reload
```

API будет доступен на `http://localhost:8000`, документация — `/docs`,
health-check — `/health`. При первом старте таблицы и демо-данные создаются
автоматически.

## 11. Docker запуск

```bash
docker compose up --build
```

- Сервис `backend` доступен на `http://localhost:8000`;
- SQLite хранится в volume `skillquest_data` (`/app/data/skillquest.db`);
- переменные окружения из `compose.yaml` (`DATABASE_URL` и др.).

## 12. Запуск тестов

```bash
# из корня репозитория (или из backend/: pytest — рабочая)
python -m pytest -c backend/pyproject.toml
pytest backend/tests/unit -q                     # только unit-тесты
pytest backend/tests/integration/test_api.py     # интеграционный сценарий
pytest -c backend/pyproject.toml --cov=backend.app --cov-report=term-missing
```

Unit-тесты покрывают: диагностику, расчёт навыков, игровые задания, фильтрацию,
рекомендации и анализ резюме. Интеграционный тест проверяет полный сценарий
через HTTP API (см. следующий раздел).

## 13. Пошаговая проверка сценария

Полный пользовательский сценарий можно проверить вручную (curl/Swagger):

```bash
BASE=http://localhost:8000

# 1. Создание пользователя
curl -s -X POST $BASE/users -H "Content-Type: application/json" \
  -d '{"name":"Студент","education":"МГТУ, 3 курс","direction":"backend","goal":"Стажировка"}' 
# → {"id":1,...}

# 2. Первичная диагностика
curl -s -X POST $BASE/users/1/assessment -H "Content-Type: application/json" \
  -d '{"answers":[{"question_id":1,"option_index":2},{"question_id":2,"option_index":1}]}'

# 3. Skill Map
curl -s $BASE/users/1/skills

# 4. Следующая миссия
curl -s "$BASE/missions/next?user_id=1"

# 5. Ответ на миссию (option_id из ответа выше)
curl -s -X POST $BASE/missions/1/answer -H "Content-Type: application/json" \
  -d '{"user_id":1,"option_id":1}'

# 6. Прогресс пользователя
curl -s $BASE/users/1/progress

# 7. Рекомендации курсов и стажировок
curl -s "$BASE/courses/recommended?user_id=1"
curl -s "$BASE/internships/recommended?user_id=1"

# 8. Загрузка резюме и анализ
curl -s -X POST $BASE/users/1/resumes -H "Content-Type: application/json" \
  -d '{"text":"Python, SQL, git. Образование: МГТУ. https://github.com/ivan"}'
curl -s -X POST $BASE/resumes/1/analyze
curl -s $BASE/resumes/1/analysis
```

Этот же сценарий автоматически проверяется
в `backend/tests/integration/test_api.py` (см. [12](#12-запуск-тестов)).

