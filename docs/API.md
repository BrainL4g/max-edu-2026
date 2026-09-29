# SkillQuest API

Игровой бэкенд SkillQuest: диагностика навыков → миссии → Skill Map →
рекомендации курсов и стажировок → анализ резюме.

- **Базовый URL** (локально): `http://localhost:8000`
- **Интерактивная документация**: `/docs` (Swagger UI)
- **OpenAPI-спецификация**: `/openapi.json`, закоммиченные `openapi.yaml` / `openapi.json`
- **Контракт приёмки**: `DATA-API.yaml` (см. раздел «Обязательные проверки»)

---

## Служебные операции

### Health-check

`GET /health` — публичная операция, проверка живости сервиса.

```json
// response
{ "status": "ok", "app": "SkillQuest", "env": "prod" }
```

### Корневая страница

`GET /` — публичная операция, ссылки на документацию.

```json
// response
{ "app": "SkillQuest", "docs": "/docs", "health": "/health" }
```

---

## Общие сведения

### Аутентификация

Защищённые операции требуют заголовок `Authorization: Bearer <токен>`.
Токены ролей `student` и `admin` хранятся в БД **только в виде хэша (SHA-256)**
— открытый текст выдаётся один раз при создании учётной записи.

| Роль      | Что умеет                                                             |
|-----------|-----------------------------------------------------------------------|
| `student` | Только свои ресурсы (`user_id` в пути обязан совпадать с владельцем токена) |
| `service` | Доступ к любому пользователю (бот MAX, `POST /users/by-max`)          |
| `admin`   | Чтение пользователей и `POST /admin/test-users/reset`                 |

| Код | Когда |
|-----|-------|
| `401 Unauthorized` | Заголовок `Authorization` отсутствует или токен невалиден |
| `403 Forbidden` | Токен валиден, но роль не даёт доступ к этому ресурсу |

### Публичные (без токена) операции

Токен **не требуется** для:

- `GET /health`, `GET /`
- `GET /roles`, `GET /skills`, `GET /skills/{skill_id}`
- `GET /courses`, `GET /courses/{course_id}`
- `GET /internships`, `GET /internships/{internship_id}`
- `GET /assessment/questions` **без** параметра `user_id` (с `user_id` — 401/403)
- `GET /consent/policy` (текст политики обработки персональных данных)

Токен **обязателен** для всех остальных операций, включая персональные
выдачи `GET /courses/recommended` и `GET /internships/recommended`
(принимают `user_id` и подбирают курсы под пробелы навыков).

### Два вида ошибки 422

| Вид | Формат тела | Когда |
|-----|-------------|-------|
| **Ошибка валидации pydantic** | `{"detail": [ {"loc": [...], "msg": "...", "type": "..."} ]}` | Тело или query не совпадает со схемой (`text` не строка, `answers` не список, `option_index` вне диапазона) |
| **Доменная ошибка** (`InvalidDataError`) | `{"detail": "Текст ошибки"}` | Данные формально валидны, но нарушают правила предметной области (например, ответ на вопрос, которого нет в диагностике) |

Код ответа в обоих случаях `422`, но тело различается: список объектов
против строки. Остальные доменные ошибки мапятся отдельно:
`NotFoundError` → `404`, `ConflictError` → `409`.

### CORS

API разрешает кросс-доменные запросы из браузера. Настройка —
`CORS_ORIGINS` в окружении: список origins через запятую, `*` — разрешить все
(значение по умолчанию разработки). В деплое перечислите origins явно,
например `CORS_ORIGINS=https://bot.example.com,https://app.example.com`.

### Формат ошибок

Ошибки приложения возвращаются в JSON:

```json
{ "detail": "Описание ошибки" }
```

| Код | Когда |
|-----|-------|
| `404 Not Found` | ресурс не найден (пользователь, миссия, роль и т.д.); анализ ещё не выполнен |
| `422 Unprocessable Entity` | некорректные входные данные (см. «Два вида ошибки 422») |
| `409 Conflict` | конфликт данных (например, дубликат) |
| `401 Unauthorized` | нет валидного Bearer-токена |
| `403 Forbidden` | роль не даёт доступ |

### Идемпотентность

| Операция | Поведение при повторе |
|----------|---------------------|
| `POST /users/by-max` | Возвращает **тот же** пользователь по `max_user_id`, ничего не создаёт |
| `POST /users` | Всегда создаёт нового пользователя (`201`) |
| `POST /admin/test-users/reset` | Всегда возвращает `200`; очищает учебные данные независимо от состояния |
| `POST /missions/{id}/answer` | Повторная сдача решённой миссии: `already_solved=true`, `xp_earned=0`, новой попытки не создаётся |
| `POST /resumes/{id}/analyze` | Всегда пересчитывает и **обновляет** результат анализа |

### Уровни навыков и XP

- Уровни навыка: `0..5`; целевой уровень для ролей — `3`.
- За верный ответ на миссию начисляется `reward_xp` + бонус за сложность
  (`easy` — 0, `medium` — 10, `hard` — 20).
- За неверный ответ опыт не начисляется.
- Повторная сдача уже решённой миссии не создаёт новой попытки и не даёт XP
  (ответ помечается `already_solved: true`).

---

## Пользователи

### Создать пользователя

`POST /users` → `201`

```json
// request
{ "name": "Студент", "education": "МГТУ, 3 курс", "direction": "backend", "goal": "Стажировка" }
```

```json
// response
{
  "id": 1,
  "name": "Студент",
  "education": "МГТУ, 3 курс",
  "direction": "backend",
  "goal": "Стажировка",
  "max_user_id": null,
  "target_role_id": null,
  "created_at": "2026-01-01T12:00:00"
}
```

### Связка пользователя платформы (get-or-create)

`POST /users/by-max`

Используется MAX-ботом на каждом `/start`. Повторный вызов возвращает
существующего пользователя, имя не перезаписывается.

```json
// request
{ "max_user_id": 42, "name": "Студент" }
```

### Профиль пользователя

`GET /users/{user_id}` — ответ как при создании пользователя.

### Обновить профиль

`PATCH /users/{user_id}`

Тело — любые поля из `{name, education, direction, goal}` (передаются только
изменяемые).

### Выбрать целевую роль

`PUT /users/{user_id}/goal`

Миссии и диагностика работают строго по целевой роли.

```json
// request
{ "target_role_id": 1 }
```

`404`, если роли с таким id нет.

### Прогресс пользователя

`GET /users/{user_id}/progress`

```json
{
  "user_id": 1,
  "total_xp": 450,
  "completed_missions": 3,
  "total_missions": 18,
  "skills_count": 5,
  "average_level": 2.2,
  "skill_map": [
    { "skill_id": 1, "name": "Python", "category": "Программирование",
      "level": 3, "experience": 300, "progress": 22.2, "next_level_xp": 450 }
  ]
}
```

`next_level_xp` — порог опыта следующего уровня (`null` на максимальном).

### Gap-анализ до целевой роли

`GET /users/{user_id}/gap-analysis`

```json
{
  "user_id": 1,
  "role": { "id": 1, "name": "Backend Junior", "direction": "backend", "level": "junior",
            "description": "...", "requirements": [
              { "skill_id": 1, "name": "Python", "category": "Программирование",
                "required_level": 3, "importance": 0.9, "is_mandatory": true }
            ] },
  "match_percent": 45,
  "items": [
    { "skill_id": 1, "name": "Python", "category": "Программирование",
      "current_level": 2, "required_level": 3, "gap": 1, "importance": 0.9, "is_mandatory": true }
  ],
  "summary": "Совпадение с ролью — 45%..."
}
```

---

## Навыки

### Все навыки

`GET /skills`

### Навык по id

`GET /skills/{skill_id}`

### Skill Map пользователя

`GET /users/{user_id}/skills` — список `SkillMapItem` (как в `/progress`).

---

## Целевые роли

### Все роли

`GET /roles`

```json
// response (элемент списка)
{
  "id": 1,
  "name": "Backend Junior",
  "direction": "backend",
  "level": "junior",
  "description": "...",
  "requirements": [
    { "skill_id": 1, "name": "Python", "category": "Программирование",
      "required_level": 3, "importance": 0.9, "is_mandatory": true }
  ]
}
```

---

## Диагностика

### Банк вопросов

`GET /assessment/questions?user_id={id}`

Если передан `user_id`, вопросы фильтруются по направлению целевой роли
пользователя (`target_role.direction`, иначе `user.direction`).

```json
// response (элемент списка)
{
  "id": 1,
  "skill": "Python",
  "text": "Как вы работаете с Python? Оцените свой уровень.",
  "options": ["Почти не писал(а): знаю только print", "..."]
}
```

### Отправить ответы

`POST /users/{user_id}/assessment`

Каждый `option_index` — номер варианта из `/assessment/questions`; результат —
начальный Skill Map.

```json
// request
{ "answers": [ { "question_id": 1, "option_index": 2 }, { "question_id": 2, "option_index": 1 } ] }
```

```json
// response
{ "user_id": 1, "evaluated_skills": [ /* SkillMapItem */ ], "summary": "..." }
```

---

## Миссии

### Все миссии

`GET /missions`

### Миссия по id

`GET /missions/{mission_id}` — варианты ответов не раскрывают правильный.

### Следующая миссия по цели

`GET /missions/next?user_id={id}`

Миссия выбирается **строго по целевой роли** пользователя: среди требований
роли, ещё не решённых на нужном уровне, по приоритету
(пробел > обязательность > важность > сложность).

```json
// response: status = "ok"
{
  "status": "ok",
  "mission": {
    "id": 4,
    "skill_id": 1,
    "skill_name": "Python",
    "difficulty": "medium",
    "scenario": "Нужно вывести сумму чисел от 1 до n включительно...",
    "explanation": "...",
    "reward_xp": 30,
    "options": [ { "id": 7, "text": "..." }, { "id": 8, "text": "..." } ]
  },
  "done": 2,
  "total": 5
}
```

| `status`   | Значение |
|------------|----------|
| `ok`       | миссия доступна, поле `mission` заполнено |
| `no_goal`  | у пользователя нет целевой роли |
| `all_done` | все миссии роли пройдены |

### Ответить на миссию

`POST /missions/{mission_id}/answer`

```json
// request
{ "user_id": 1, "option_id": 7 }
```

```json
// response
{
  "attempt_id": 101,
  "mission_id": 4,
  "is_correct": true,
  "xp_earned": 40,
  "explanation": "...",
  "correct_option_id": 7,
  "correct_option_text": "...",
  "skill_id": 1,
  "skill_name": "Python",
  "skill_level_before": 2,
  "skill_level_after": 3,
  "already_solved": false
}
```

За неверный ответ `xp_earned = 0`; при повторной сдаче решённой миссии —
`already_solved: true` и `xp_earned = 0`.

### Результат попытки

`GET /attempts/{attempt_id}` — ответ в формате `AttemptResultOut` выше.

### История попыток пользователя

`GET /users/{user_id}/attempts`

```json
// response (элемент списка)
{
  "id": 101,
  "mission_id": 4,
  "is_correct": true,
  "status": "solved",
  "xp_earned": 40,
  "created_at": "2026-01-01T12:00:00"
}
```

---

## Курсы

### Список с фильтрами

`GET /courses`

| Параметр     | Тип      | Описание |
|--------------|----------|----------|
| `search`     | `str`    | поиск по названию и описанию |
| `skills`     | `str`    | id навыков через запятую |
| `category`   | `str`    | категория |
| `level`      | `str`    | уровень (beginner/advanced и т.д.) |
| `price_max`  | `float`  | максимальная цена |
| `format`     | `str`    | формат (online/offline и т.д.) |
| `platform`   | `str`    | платформа |

```json
// response (элемент списка)
{
  "id": 1,
  "title": "Python для анализа данных",
  "description": "...",
  "platform": "Stepik",
  "url": "https://stepik.org/1",
  "level": "beginner",
  "category": "Данные",
  "cost": 0.0,
  "format": "online",
  "skills": [ { "id": 1, "name": "Python", "category": "Программирование", "description": null } ]
}
```

### Рекомендации по пробелам

`GET /courses/recommended?user_id={id}` — те же query-параметры фильтрации.
Курсы подбираются по пробелам в навыках пользователя (целевые навыки курса ∩
недостающие навыки).

### Курс по id

`GET /courses/{course_id}`

---

## Стажировки

### Список с фильтрами

`GET /internships`

| Параметр    | Тип     | Описание |
|-------------|---------|----------|
| `search`    | `str`   | поиск по названию, компании, описанию |
| `direction` | `str`   | направление (backend/frontend/data/...) |
| `skills`    | `str`   | id навыков через запятую |
| `level`     | `str`   | уровень |
| `city`      | `str`   | город |
| `remote`    | `bool`  | только удалённые |
| `format`    | `str`   | формат |

```json
// response (элемент списка)
{
  "id": 1,
  "title": "Стажёр-разработчик Backend",
  "company": "SkillQuest",
  "description": "...",
  "url": "https://ya.ru/vacancy",
  "level": "intern",
  "city": "Москва",
  "remote": false,
  "format": "full-time",
  "requirements": "Python, SQL, Git",
  "direction": "backend",
  "skills": [ { "id": 1, "name": "Python", "category": "Программирование", "description": null } ]
}
```

### Направления

`GET /internships/directions` — список доступных направлений для фильтра (например, `["backend", "frontend", ...]`).

### Рекомендации

`GET /internships/recommended?user_id={id}` — те же query-параметры.
Учитывается направление целевой роли пользователя и совпадение навыков.

### Стажировка по id

`GET /internships/{internship_id}`

---

## Резюме

### Загрузить текстом

`POST /users/{user_id}/resumes` → `201`

```json
// request
{ "text": "Python, SQL, git. Образование: МГТУ.", "filename": "resume.txt" }
```

### Загрузить файлом

`POST /users/{user_id}/resumes/upload` → `201`

Multipart-форма, поле `file` (текстовые форматы: txt/md и др.).

### Резюме пользователя

`GET /users/{user_id}/resumes`

### Резюме по id

`GET /resumes/{resume_id}`

```json
{
  "id": 1,
  "user_id": 1,
  "filename": "resume.txt",
  "text": "Python, SQL, git. Образование: МГТУ.",
  "uploaded_at": "2026-01-01T12:00:00"
}
```

### Запустить анализ

`POST /resumes/{resume_id}/analyze`

### Результат анализа

`GET /resumes/{resume_id}/analysis` — `404`, если анализ ещё не выполнен.

```json
{
  "resume_id": 1,
  "found_skills": ["Python", "SQL", "Git"],
  "missing_skills": ["Docker", "Алгоритмы и структуры данных"],
  "strengths": ["Указано образование"],
  "issues": ["Нет контактов"],
  "recommendations": ["Добавьте ссылку на GitHub"],
  "direction_match": 40.0,
  "summary": "Резюме закрывает 40% требований направления..."
}
```

---

## Персональные данные (152-ФЗ)

Обработка ПД описана в `POLICY_TEXT` (`GET /consent/policy`). Ниже — операции,
реализующие права субъекта: согласие, копия данных и удаление.

### Политика обработки

`GET /consent/policy` — публичная операция (без токена).

```json
// response 200
{ "text": "Политика обработки персональных данных SkillQuest...", "version": "1.0" }
```

### Согласие на обработку

Согласие фиксируется явно и по умолчанию **отсутствует** (`consent_given=false`).
Оно не удаляет уже собранные данные — для этого есть операция удаления ниже.

`GET /users/{user_id}/consent` — текущее состояние согласия.

`POST /users/{user_id}/consent` — зафиксировать согласие (152-ФЗ ст. 9).

`DELETE /users/{user_id}/consent` — отозвать согласие (ст. 9, п. 6).

```json
// response 200 — после POST
{
  "user_id": 1,
  "consent_given": true,
  "consent_at": "2026-09-29T12:00:00",
  "policy_version": "1.0"
}
```

Бот спрашивает согласие перед приёмом резюме: кнопка «📄 Резюме» без
зафиксированного согласия показывает экран согласия с кнопками
«✅ Согласен» и «❌ Не согласен». При «Согласен» бот вызывает
`POST /users/{user_id}/consent` и только потом просит прислать резюме; если
запрос не прошёл, резюме не принимается. На экране ожидания есть кнопка
«🚫 Отозвать согласие» → `DELETE /users/{user_id}/consent`.

### Копия данных

`GET /users/{user_id}/data-export` — ст. 14: копия всех персональных данных
субъекта (профиль, идентификатор MAX, целевая роль, состояние согласия).

```json
// response 200
{
  "user_id": 1,
  "name": "Иван Иванов",
  "education": "МГТУ, 3 курс",
  "direction": "backend",
  "goal": "Попасть на стажировку",
  "max_user_id": 12345,
  "target_role_id": 1,
  "consent_given": true,
  "consent_at": "2026-09-29T12:00:00",
  "consent_policy_version": "1.0",
  "created_at": "2026-09-20T09:00:00"
}
```

### Удаление данных

`DELETE /users/{user_id}/data` — ст. 3 п. 5: право на забвение. Удаляются
профиль, Skill Map, попытки по миссиям, резюме с результатами анализа и
токены доступа — одной транзакцией. Запись в журнале аудита остаётся без
связки с удалённым субъектом.

```json
// response 200
{ "user_id": 1, "deleted": true, "message": "Персональные данные пользователя удалены" }
```

> Все операции раздела доступны владельцу данных и роли `service` (бот).
> Для чужого `user_id` — `403`.

### Защита данных при хранении

| Поле | Хранение |
|------|----------|
| `users.name`, `users.education`, `users.direction`, `users.goal` | шифротекст `enc:v1:<Fernet>` |
| `resumes.text`, `resumes.filename` | шифротекст `enc:v1:<Fernet>` |
| `api_tokens.token_hash` | SHA-256 хэш, открытый токен не хранится |

Ключ — `DATA_ENCRYPTION_KEY` (Fernet, base64url, 32 байта). При
`APP_ENV=production` без корректного ключа приложение не стартует.

Значения, записанные до включения шифрования, не имеют префикса `enc:v1:`,
читаются как есть и перешифровываются при следующей записи.

### Журнал аудита

Обращения к персональным данным пишутся в лог `skillquest.audit` с
префиксом `AUDIT:`: действие (`read`/`create`/`update`/`export`/`delete`),
ресурс, id, роль и id субъекта. Значения полей в журнал не попадают.

---

## Администрирование

### Сброс тестовых данных

`POST /admin/test-users/reset` — только роль `admin`
(`401` без токена, `403` для `student`/`service`).

Очищает `Attempt`, `Skill Map`, `Resume`, `ResumeAnalysis` и сбрасывает
`target_role_id` у тест-студентов (`is_test=true`). `user_id` и токены
**не меняются**, поэтому сценарий можно повторять без пересева.

```json
// response 200
{ "reset": true, "students_affected": 1, "message": "Учебные данные тест-студентов сброшены" }
```

---

## Тестовые аккаунты

### Создание / пересоздание

```bash
# из корня репозитория
python -X utf8 scripts/seed_test_accounts.py           # создать (однократно, ConflictError при повторе)
python -X utf8 scripts/seed_test_accounts.py --reset   # удалить и пересоздать (новые id + токены)
```

Скрипт печатает `user_id` и Bearer-токены **один раз** (в БД хранится только хэш):

```
student: user_id=1 token=<случайный>
admin:   user_id=2 token=<случайный>
```

| Роль | Учётная запись |
|------|---------------|
| `student` | `is_test=True`; все учебные данные сбрасываются через `/admin/test-users/reset` |
| `admin` | `is_test=False`; `POST /admin/test-users/reset` |

### Сброс учебных данных

`POST /admin/test-users/reset` — требует роль `admin`. Очищает
`Attempt`, `Skill Map`, `Resume`, `ResumeAnalysis` и сбрасывает
`target_role_id` у тест-студентов. `user_id` и токены **не меняются**.

```json
// response
{ "reset": true, "students_affected": 1, "message": "Учебные данные тест-студентов сброшены" }
```

---

## Обязательные проверки (DATA-API)

Файл `DATA-API.yaml` в корне репозитория описывает полный набор проверок
приёмки. Каждая проверка содержит ровно 9 полей: `name`, `description`,
`method`, `path`, `params`, `role`, `expected_status`, `content_type`,
`required_fields`. Ключи (токены) вынесены в раздел `keys`.

### Локальный прогон (через `TestClient`)

```bash
cd backend
python -m pytest tests/contract/test_data_api.py::test_all_data_api_checks_pass -v
```

### Прогон по HTTP (через Caddy)

```bash
python -X utf8 scripts/run_data_api.py --base-url http://localhost \
  --token student:<токен> --token admin:<токен> --token service:<токен>
```

---

## Полный сценарий

```bash
BASE=http://localhost:8000
TOKEN=<токен тест-студента>   # из scripts/seed_test_accounts.py
AUTH="Authorization: Bearer $TOKEN"
JSON="Content-Type: application/json"

# 0. Сброс учебных данных (роль admin) — делает прогон воспроизводимым
curl -s -X POST $BASE/admin/test-users/reset -H "Authorization: Bearer <токен admin>"

# 1. Создание пользователя
curl -s -X POST $BASE/users -H "$AUTH" -H "$JSON" \
  -d '{"name":"Студент","direction":"backend"}'

# 2. Выбор целевой роли
curl -s -X PUT $BASE/users/1/goal -H "$AUTH" -H "$JSON" \
  -d '{"target_role_id":1}'

# 3. Диагностика (банк вопросов → ответы → Skill Map)
curl -s "$BASE/assessment/questions?user_id=1" -H "$AUTH"
curl -s -X POST $BASE/users/1/assessment -H "$AUTH" -H "$JSON" \
  -d '{"answers":[{"question_id":1,"option_index":2}]}'

# 4. Миссия строго по цели → ответ → результат
curl -s "$BASE/missions/next?user_id=1" -H "$AUTH"
curl -s -X POST $BASE/missions/4/answer -H "$AUTH" -H "$JSON" \
  -d '{"user_id":1,"option_id":7}'

# 5. Прогресс и рекомендации
curl -s $BASE/users/1/progress -H "$AUTH"
curl -s "$BASE/courses/recommended?user_id=1" -H "$AUTH"
curl -s "$BASE/internships/recommended?user_id=1" -H "$AUTH"

# 6. Резюме и анализ
curl -s -X POST $BASE/users/1/resumes -H "$AUTH" -H "$JSON" \
  -d '{"text":"Python, SQL. Образование: МГТУ."}'
curl -s -X POST $BASE/resumes/1/analyze -H "$AUTH"
curl -s $BASE/resumes/1/analysis -H "$AUTH"

# 7. Проверки доступа: 401 без токена, 403 на чужой ресурс
curl -s -o /dev/null -w "%{http_code}\n" $BASE/users/1            # 401
curl -s -o /dev/null -w "%{http_code}\n" $BASE/users/2 -H "$AUTH" # 403
```