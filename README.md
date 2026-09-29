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
13. [Проверка API](#13-проверка-api)
14. [Пошаговая проверка сценария](#14-пошаговая-проверка-сценария)
15. [Известные ограничения](#15-известные-ограничения)

---

## 1. Что такое SkillQuest

**SkillQuest** — игровое приложение, которое помогает студентам:

- понять свой текущий уровень навыков (Skill Map);
- прокачивать навыки через короткие игровые задания-миссии;
- получать персональные рекомендации курсов и стажировок;
- проверять и улучшать резюме.

Backend реализован на **Python + FastAPI + SQLAlchemy + SQLite**, разворачивается
в **Docker**. Весь функционал доступен через HTTP API: см.
[API-документацию](docs/API.md) и [проверку API](#13-проверка-api).

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

- 🎯 **Целевая роль** — выбор карьерной цели (Backend, Frontend, QA, Data Analyst,
  ML Trainee, UI/UX Designer). От роли зависят вопросы диагностики, подбор миссий
  и gap-анализ соответствия в Skill Map.
- 🧠 **Диагностика** — первичная оценка навыков по категориям.
- 🎮 **Миссии** — игровые задания с вариантами ответов, XP и уровнями.
  - Миссии подбираются **строго по целевой роли** (`target_role_id`): без цели бот просит её выбрать, всё пройденное по роли отмечается как «всё пройдено».
  - **Честный XP**: за неверный ответ опыт не начисляется; верный ответ приносит XP **один раз** — повторная сдача уже решённой миссии не создаёт новых попыток и не добавляет опыта.
- 📊 **Skill Map** — уровни и прогресс по каждому навыку.
- 📚 **Курсы** — список, поиск, фильтрация, рекомендации по пробелам.
- 💼 **Стажировки** — список, фильтрация, рекомендации по направлению и навыкам.
- 📄 **Резюме** — загрузка (текст/файл), анализ, отчёт с проблемами и советами.
- 🏷️ **Фильтрация** курсов: `skill`, `category`, `level`, `price`, `format`, `platform`.
- 🏷️ **Фильтрация** стажировок: `direction`, `skills`, `level`, `city`, `remote`, `format`.

## 5. Архитектура

```text
Пользователь в MAX ──► MAX-бот (bot/, maxapi) ──► FastAPI (backend/) ──► SQLite
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
MAX_BOT_TOKEN=
PUBLIC_BASE_URL=http://localhost:8000
SERVICE_API_TOKEN=
```

| Переменная | Значение | По умолчанию |
|-----------|----------|--------------|
| `APP_NAME` | Название приложения | `SkillQuest` |
| `APP_ENV` | `development` / `testing` / `production` | `development` |
| `DATABASE_URL` | URL SQLite (или другой БД через SQLAlchemy) | `sqlite:///./skillquest.db` |
| `MAX_BOT_TOKEN` | Токен бота (для внешней интеграции) | пусто |
| `PUBLIC_BASE_URL` | Публичный адрес API (попадает в `servers` OpenAPI) | `http://localhost:8000` |
| `SERVICE_API_TOKEN` | Bearer-токен сервисной роли для MAX-бота | пусто |
| `AUTO_CREATE_TABLES` | Создавать таблицы при старте (прототип) | `true` |
| `SEED_ON_STARTUP` | Наполнять базу демо-данными при старте | `true` |
| `CORS_ORIGINS` | Разрешённые origins через запятую | `*` |

> ⚠️ Рабочие токены в Git не хранятся: `.env` в `.gitignore`, в примере — только шаблон.

## 8. Данные

**БД SQLite.** Основные таблицы:

```text
users             profiles, направление, цель
roles            целевые карьерные роли (название, направление, уровень)
role_skills      требования роли к навыкам (уровень, важность, обязательность)
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
users ── target_role ── roles
roles ── role_skills ── skills
courses ── course_skills ── skills
internships ── internship_skills ── skills
```

**Демо-данные.** При `SEED_ON_STARTUP=true` база наполняется 16 навыками,
43 миссиями, 14 курсами и 8 стажировками. Повторный запуск идемпотентен.
Ручной запуск (из корня): `python -m backend.app.seed`.

**Миграции.** Схема управляется Alembic (`backend/alembic/`):
`001_initial_schema.py` (основные таблицы), `002_add_resume_analysis.py`
(резюме и анализ), `003_add_max_user_id.py` (связка с пользователями MAX),
`004_add_roles.py` (целевые карьерные роли и их требования),
`005_add_api_tokens.py` (таблица `api_tokens` — Bearer-токены ролей
`student` и `admin`).
Применение (из корня): `alembic -c backend/alembic.ini upgrade head`.

> Если dev-база создана через `create_all` до введения Alembic (в ней нет
> таблицы `alembic_version`), приведите её к актуальной схеме так:
> `alembic -c backend/alembic.ini stamp 002 && alembic -c backend/alembic.ini upgrade head`
> (команда выполняется из каталога, где лежит файл базы).

## 9. Интеграции

- **CORS** — настроен: переменная `CORS_ORIGINS` задаёт разрешённые origins
  через запятую, `*` разрешает все (по умолчанию).
- **Swagger UI** — встроенная документация API на `/docs`.
- **OpenAPI** — спецификация на `/openapi.json` (для генерации клиентов).
- **API-документация** — подробное описание всех эндпоинтов, схем ответов
  и примеров запросов в [docs/API.md](docs/API.md).

### Использование API из кода (Python)

Роутеры вынесены в пакет `backend.app.api.routes` и подключаются единым
`api_router` (см. `backend/app/api/router.py`). Пример:

```python
from backend.app.api.routes import (
    assessment,
    courses,
    internships,
    missions,
    resumes,
    skills,
    users,
)
from fastapi import FastAPI

app = FastAPI()
for module in (users, skills, assessment, missions, courses, internships, resumes):
    app.include_router(module.router)
```

Каждый модуль экспонирует объект `fastapi.APIRouter` в `module.router`,
поэтому роутеры можно подключать выборочно.

### MAX-бот

Бот живёт в `bot/` и работает поверх готового API — вся логика на бэкенде,
бот только показывает экраны и кнопки:

```text
main.py        точка входа (polling через maxapi)
api.py         HTTP-клиент к API SkillQuest
keyboards.py   inline-кнопки (меню, варианты ответов, ссылки)
texts.py       форматирование Skill Map, миссий, рекомендаций, резюме
handlers/      start, goal, missions, assessment, skillmap, recommend,
               resume, fallback (свободный текст → меню-подсказка)
sessions.py    легковесное состояние (uid, ответы диагностики, флаг резюме)
```

Для бэкенда добавлены два эндпоинта, которые использует бот:

- `POST /users/by-max` — связка MAX-пользователя: get-or-create по `max_user_id`
  (вызывается на каждом `/start`; миграция `003`);
- `GET /assessment/questions` — банк вопросов диагностики для показа в боте.

Локальный запуск (токен — из `MAX_BOT_TOKEN` в `.env`):

```bash
cd bot
pip install -r requirements.txt
python main.py
```

## 10. Установка

```bash
# 1. Клонировать репозиторий
git clone <repo-url> && cd max-edu-2026

# 2. Создать окружение и установить зависимости (из папки backend/)
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # Linux/macOS
pip install -r requirements.txt
pip install pytest httpx pytest-cov ruff

# 3. Установить пакет в режиме разработки — `backend.app.*` импортируется из любой папки
pip install -e .

# 4. Настроить окружение (корень репозитория)
copy ..\.env.example ..\.env

# 5. Запустить API (из корня или из backend/ — работает в обоих случаях)
cd ..
uvicorn backend.app.main:app --reload
```

API будет доступен на `http://localhost:8000`, документация — `/docs`,
health-check — `/health`. При первом старте таблицы и демо-данные создаются
автоматически.

## 11. Docker запуск

```bash
docker compose up --build
```

```text
backend   FastAPI + SQLite (доступен только по внутренней сети, наружу не торчит)
bot       MAX-бот (maxapi, httpx); токен и адрес API — из окружения
caddy     HTTPS-вход (80/443 наружу), reverse_proxy на backend:8000
```

- SQLite хранится в volume `skillquest_data` (`/app/data/skillquest.db`);
- `MAX_BOT_TOKEN` подхватывается из `.env` в корне репозитория;
- для разработки к `backend` можно вернуть `ports: ["8000:8000"]` в `compose.yaml`.

### Деплой за HTTPS (Caddy + Let's Encrypt)

Единственная точка входа наружу — контейнер `caddy`: он терминирует TLS и
проксирует запросы на `backend:8000` во внутренней сети Docker. Порт `8000`
наружу не публикуется, поэтому backend напрямую из интернета недоступен.

```bash
# 1. Заполнить .env (корень репозитория)
SITE_ADDRESS=api.example.com             # домен для сертификата
ACME_EMAIL=dev@example.com               # email для уведомлений Let's Encrypt
PUBLIC_BASE_URL=https://api.example.com  # попадает в servers OpenAPI
SERVICE_API_TOKEN=<случайная строка>     # сервисная роль, её использует бот
CORS_ORIGINS=https://bot.example.com     # явный список origins, без '*'

# 2. Поднять стек
docker compose up -d --build

# 3. Проверить
curl -sSf https://api.example.com/health
curl -sSf -o /dev/null -w '%{http_code}\n' https://api.example.com/docs   # 200
```

Сертификат выпускается и продлевается автоматически (ACME-челленджи и
сертификаты — в volume `caddy_data`). Для локальной проверки без домена
поставьте `SITE_ADDRESS=:80` — тогда Caddy поднимет обычный HTTP на 80.

## 12. Запуск тестов

```bash
# из корня репозитория (или из backend/: pytest — рабочая)
python -m pytest -c backend/pyproject.toml
pytest backend/tests/unit -q                     # только unit-тесты
pytest backend/tests/integration/test_api.py     # интеграционный сценарий
pytest -c backend/pyproject.toml --cov=backend.app --cov-report=term-missing

# тесты MAX-бота (из папки bot/) — без сети и API, на фейк-событиях
cd bot
python -m pytest
```

Unit-тесты backend покрывают: диагностику, расчёт навыков, игровые задания,
фильтрацию, рекомендации, анализ резюме, репозитории, исключения и seed.
Интеграционный тест проверяет полный сценарий через HTTP API (см. следующий
раздел). Покрытие backend — 100% (`fail_under = 90` в `backend/pyproject.toml`).

Тесты MAX-бота (`bot/tests/`) проверяют: форматирование текстов, inline-клавиатуры,
сессии, HTTP-клиент (MockTransport, без сети), все хендлеры (диагностика, миссии,
Skill Map, рекомендации, резюме, fallback на свободный текст, старт), а также
токен-гард и обработчик ошибок точки входа.

### Статический анализ и форматирование

Инструменты: `black`, `isort`, `autoflake`, `ruff`, `mypy --strict`
(устанавливаются в dev-зависимостях backend; конфигурация — в
`backend/pyproject.toml` и `bot/pyproject.toml`).

```bash
# из папки backend/
python -m black app tests
python -m isort app tests
python -m autoflake --in-place --recursive --remove-all-unused-imports app
python -m ruff check app
python -m mypy app            # mypy --strict (настроено в pyproject.toml)

# из папки bot/
python -m black .
python -m isort .
python -m ruff check .
python -m mypy .
```

## 13. Проверка API

Полный контракт приёмки — в файле [`DATA-API.yaml`](DATA-API.yaml) (в корне
репозитория). Каждая проверка описывает 9 полей: `name`, `description`,
`method`, `path`, `params`, `role`, `expected_status`, `content_type`,
`required_fields`; токены вынесены в раздел `keys`.

### Локально (через TestClient, без сети)

```bash
# из backend/ — прогон всех проверок + сверка структуры и OpenAPI
python -m pytest tests/contract -v
```

### По публичному адресу

```bash
# 1. Получить тестовые токены (печатаются один раз)
python -X utf8 scripts/seed_test_accounts.py

# 2. Прогнать DATA-API по HTTPS
python -X utf8 scripts/run_data_api.py \
  --base-url https://<домен> \
  --token student=<токен> --token admin=<токен> \
  --user-id 1 --admin-id 2
```

Сбросить учебные данные тест-студента (роль `admin`) можно в любой момент:

```bash
curl -s -X POST $BASE/admin/test-users/reset -H "Authorization: Bearer <токен admin>"
```

Тест-данные для сценариев — [`tests-data/test-data.json`](tests-data/test-data.json)
(профиль студента, эталонные ответы диагностики, текст резюме без ПДн).

## 14. Пошаговая проверка сценария

Полный пользовательский сценарий можно проверить вручную (curl/Swagger).
Справочник всех эндпоинтов, схем и примеров — в
[API-документации](docs/API.md):

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

# 4. Цель (миссии и диагностика работают по целевой роли)
curl -s -X PUT $BASE/users/1/goal -H "Content-Type: application/json" -d '{"target_role_id":1}' 
# → {"id":1,"target_role_id":1,...}

# 5. Следующая миссия → {"status":"ok|no_goal|all_done","done":N,"total":M,"mission":{...}}
curl -s "$BASE/missions/next?user_id=1"

# 6. Ответ на миссию (option_id из ответа выше)
curl -s -X POST $BASE/missions/1/answer -H "Content-Type: application/json" \
  -d '{"user_id":1,"option_id":1}'

# 7. Прогресс пользователя
curl -s $BASE/users/1/progress

# 8. Рекомендации курсов и стажировок
curl -s "$BASE/courses/recommended?user_id=1"
curl -s "$BASE/internships/recommended?user_id=1"

# 9. Загрузка резюме и анализ
curl -s -X POST $BASE/users/1/resumes -H "Content-Type: application/json" \
  -d '{"text":"Python, SQL, git. Образование: МГТУ. https://github.com/ivan"}'
curl -s -X POST $BASE/resumes/1/analyze
curl -s $BASE/resumes/1/analysis
```

Этот же сценарий автоматически проверяется
в `backend/tests/integration/test_api.py` (см. [12](#12-запуск-тестов)).

## 15. Известные ограничения

- **Диагностика строится на самооценке.** Уровни навыков в Skill Map берутся из
  ответов пользователя на вопросы диагностики; завышенная самооценка завышает и
  совпадение с ролью. Миссии дают объективную обратную связь (верно/неверно), но
  пока не смешиваются с самооценкой в одном показателе.
- **Анализ резюме эвристический.** Навыки ищутся в тексте по точному совпадению
  фраз; короткие алиасы могут давать ложные срабатывания, а опечатки — пропуски.
- **Каталог курсов и стажировок статичен.** Ссылки и условия никто не проверяет
  автоматически — со временем часть может устареть.
- **SQLite в одном файле.** Подходит для одного инстанса; при нескольких репликах
  понадобится PostgreSQL. Миграции — Alembic.
- **Сессии бота в памяти.** Состояние (uid, ответы диагностики, флаг резюме)
  живёт в памяти процесса и сбрасывается при рестарте бота.
- **Роли выдаются скриптом, без UI.** Токены `student`/`admin` создаёт
  `scripts/seed_test_accounts.py`; отдельной админки и регистрации нет.
- **Свободный текст.** Бот отвечает кнопками и командами; произвольный текст вне
  режима «Резюме» получает подсказку с главным меню, а не содержательный ответ.

