# Тестирование

Как проверить SkillQuest: автоматические тесты, контракт по
`DATA-API.yaml` и ручной прогон в живом мессенджере.

---

## 1. Подготовка

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # Linux, macOS

pip install -r backend/requirements.txt
pip install -r bot/requirements.txt
pip install pytest pytest-cov ruff black isort mypy
```

Зависимости для backend: `pypdf` и `python-docx` нужны не только в
продакшене, но и тестам — без них ветки разбора PDF и DOCX не
покрываются.

---

## 2. Автоматические тесты

### Backend

```bash
cd backend
python -m pytest                                  # 234 теста
python -m pytest --cov --cov-report=term-missing  # с покрытием
python -m pytest tests/contract                   # только контрактные
python -m pytest tests/integration -k privacy      # только права субъекта
```

Требование к покрытию — **100%**, порог в `pyproject.toml` — 90%.
Непокрытая строка в `app/` — не 100%, и это повод написать тест, а не
добавить `# pragma: no cover`.

### Бот

```bash
cd bot
python -m pytest                                  # 162 теста
python -m pytest -k consent                       # согласие на ПД
```

Тесты бота не ходят в сеть: `bot/tests/fakes.py` подменяет события MAX,
`bot/tests/test_handlers.py` — вызовы API. Всё детерминировано.

### Линтеры

```bash
cd backend
python -m ruff check app tests
python -m black --check app tests
python -m isort --check-only app tests
python -m mypy app

cd ../bot
python -m ruff check .
python -m black --check .
python -m isort --check-only .
python -m mypy .
```

`mypy` запускается по `app`, а не по `tests`: тесты намеренно оставлены
без строгих аннотаций.

---

## 3. Контракт по `DATA-API.yaml`

27 проверок, 4 роли: `none`, `student`, `admin`, `service`. Файл — источник
правды: и раннер, и тест `tests/contract/test_data_api.py` читают его.

### Локально, через TestClient

```bash
cd backend
python -m pytest tests/contract/test_data_api.py -v
```

### По HTTP через Caddy

```bash
# 1. Поднять стек
docker compose up -d --build

# 2. Пересоздать тестовые учётки и получить токены
docker compose exec -T backend python -X utf8 -c "
import sys, json
sys.path.insert(0, '/app')
from backend.app.database.session import SessionLocal
from backend.app.services.test_accounts import TestAccountsService
db = SessionLocal()
r = TestAccountsService(db).reset()
print(json.dumps({
    'student_user': r.student.user_id, 'student_token': r.student.token,
    'admin_user':   r.admin.user_id,   'admin_token':   r.admin.token,
}))
db.close()"

# 3. Прогнать DATA-API
python scripts/run_data_api.py \
  --base-url http://localhost \
  --token student=<токен> \
  --token admin=<токен> \
  --token service=<SERVICE_API_TOKEN> \
  --user-id <student_user> \
  --admin-id <admin_user>
```

Ожидается `27/27 проверок пройдено`, `FAIL` — ноль. Раннер печатает
название и причину каждого `FAIL`.

`--base-url http://localhost` идёт через Caddy, то есть проверяет ещё и
TLS-конфигурацию. `http://localhost:8000` недоступен снаружи: порт не
проброшен.

### Синхронизация OpenAPI

`openapi.json` и `openapi.yaml` закоммичены и проверяются тестом
`tests/contract/test_openapi_contract.py`. После изменения схемы:

```bash
python scripts/export_openapi.py
```

Тест также сверяет `docs/API.md` с реальными путями: каждый путь из
OpenAPI должен встречаться в документе.

---

## 4. Ручная проверка в живом MAX

Полный сценарий на реальном боте. Ничего из этого не покрыто
автотестами: коды кнопок, перерисовка сообщений и поведение площадки
живут только здесь.

### Подготовка

```bash
docker compose up -d --build
docker compose ps                                # все три сервиса Up
docker compose logs -f bot                       # опрос событий
```

### 4.1 Приветствие

| Шаг | Ожидание |
|---|---|
| Удалить и заново добавить бота | **одно** приветствие с меню |
| Отправить `/start` | меню, приветствия нет |

Проверка на дубликат: MAX шлёт и `bot_started`, и `/start`; дедупликация
детерминированная, но поломка флага `welcomed` её снимет.

### 4.2 Роли доступа

Проверить с токеном `student`:

| Запрос | Ожидание |
|---|---|
| `GET /users/{свой_id}` без токена | `401` |
| `GET /users/{свой_id}` со своим токеном | `200` |
| `GET /users/{чужой_id}` со своим токеном | `403` |
| `POST /users/by-max` со своим токеном | `403` (только `service`) |
| `POST /admin/test-users/reset` со своим токеном | `403` (только `admin`) |

### 4.3 Цель

| Шаг | Ожидание |
|---|---|
| 🎯 Цель | список ролей кнопками |
| Выбрать роль | «Цель: <роль>», процент, «Не хватает: …» |
| 🎯 Цель повторно | список ролей, не пустой экран |

### 4.4 Диагностика

| Шаг | Ожидание |
|---|---|
| 🧠 Диагностика без цели | «Сначала выбери цель» + кнопка выбора |
| 🧠 Диагностика с целью | «Вопрос 1/N», навык, варианты |
| Ответить на все вопросы | «Диагностика завершена», сводка, меню |
| Пройти заново | уровень не падает ниже прежнего |

### 4.5 Миссия

| Шаг | Ожидание |
|---|---|
| 🎮 Миссия без цели | «Сначала выбери цель» |
| 🎮 Миссия | «Миссия 1/N по цели», сценарий, 4 варианта |
| Перезагрузить сообщение | тот же порядок вариантов |
| Ответить верно | «✅ Верно!», XP, уровень `было → стало` |
| Ответить верно ещё раз | «🔁 Уже решено», XP не начислен |
| Ответить неверно | «❌ Не совсем», верный вариант, объяснение |
| Пройти все по роли | «По цели пройдено всё (N/N)» |

### 4.6 Skill Map

| Шаг | Ожидание |
|---|---|
| 📊 Skill Map до диагностики | «Навыки ещё не оценены» |
| 📊 Skill Map после диагностики | строки с уровнем и полосой прогресса |
| 📊 Skill Map после миссии | опыт вырос, прогресс пересчитан |

### 4.7 Резюме и согласие

Ключевой сценарий по 152-ФЗ.

| Шаг | Ожидание |
|---|---|
| 📄 Резюме | **экран согласия**, а не «пришли резюме» |
| «✅ Согласен» | «Пришли резюме…» + кнопки Отозвать / Назад |
| «❌ Не согласен» | «обрабатывать не буду», остальные разделы работают |
| «📄 Политика» | текст политики, права, упоминание GigaChat |
| **Прислать резюме без согласия** | **текст не уходит**, предлагается подсказка с меню |
| Прислать текст резюме | процент соответствия, навыки, советы |
| Прислать файл PDF | то же; отчёт в новом сообщении |
| Прислать файл 6 МБ | «слишком большой», максимум 5 МБ |
| Прислать файл `.exe` | «формат не поддерживается, нужен PDF, DOCX или TXT» |
| Написать «отмена» в режиме ожидания | «Отменил 🙌», меню |
| «⬅️ Назад» в режиме ожидания | главное меню, и следующий текст **не** уходит в анализ |
| «🚫 Отозвать согласие» | «отозвано», главное меню |
| «🗑 Удалить резюме» в отчёте | «резюме удалено», меню; в списке резюме его нет |
| 📄 Резюме после удаления | снова экран ожидания, анализ стартует заново |
| 📄 Резюме после отзыва | снова экран согласия |

Проверка на сервере, что согласие записалось:

```bash
docker compose logs backend | grep 'AUDIT' | grep 'give_consent'
```

### 4.8 Свободный текст и команды

| Шаг | Ожидание |
|---|---|
| Написать произвольный текст | «Я умею команды и кнопки меню 🙂» + меню |
| Написать `/help` | инструкция |
| Написать `/start` | меню |
| Написать `/cancel` вне режима резюме | подсказка с меню |
| Написать текст с картинкой вне режима | подсказка с меню |

### 4.9 Рекомендации

| Шаг | Ожидание |
|---|---|
| 📚 Курсы | карточки ссылками, пагинация по 5 |
| 💼 Стажировки | экран выбора направления |
| Выбрать направление | стажировки по нему |
| «🌐 Все направления» | список без фильтра |
| Курсы при пустом Skill Map | пустой список, а не весь каталог |

### 4.10 Устойчивость

| Шаг | Ожидание |
|---|---|
| Остановить backend | бот пишет ошибку, **опрос продолжается** |
| Поднять backend | кнопки снова работают |
| `docker compose restart bot` | бот стартует, состояние диалога сброшено |

Последний пункт — ожидаемое поведение: сессии в памяти, согласие и
цель сохраняются в БД, поэтому вопрос о согласии задаётся заново.

---

## 5. Признаки сбоя

| Симптом | Причина |
|---|---|
| `401` на кнопках бота | бот и backend получили разные `SERVICE_API_TOKEN` — перезапустить оба сервиса |
| Кнопки не отвечают, в логах `ApiError` | backend недоступен по внутренней сети |
| Два приветствия | сломан флаг `welcomed` в `bot/sessions.py` |
| Резюме не принимается | не зафиксировано согласие; проверить `AUDIT` и `POST /consent` |
| `ValueError: не удалось расшифровать` | сменили `DATA_ENCRYPTION_KEY` — вернуть прежний или перешифровать |
| `RuntimeError: DATA_ENCRYPTION_KEY обязателен` | `APP_ENV=production` без ключа |
| `no such column` / `NOT NULL constraint failed` | миграции не применены: `alembic upgrade head` |
| `422` на загрузке файла | неподдерживаемый формат или файл больше 5 МБ |
| `openapi.yaml не совпадает` | перегенерировать `python scripts/export_openapi.py` |

---

## 6. Перед отправкой

```bash
cd backend
python -m pytest --cov --cov-report=term-missing
python -m ruff check app tests && python -m black --check app tests
python -m isort --check-only app tests && python -m mypy app
python scripts/export_openapi.py
cd ../bot
python -m pytest
python -m ruff check . && python -m black --check . && python -m mypy .
cd ..
git status --short        # пусто
```

Затем — ручной сценарий 4.7 на живом MAX: он единственный проверяет
согласие так, как его увидит человек.
