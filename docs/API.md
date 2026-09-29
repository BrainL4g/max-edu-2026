# SkillQuest API

Игровой бэкенд SkillQuest: диагностика навыков → миссии → Skill Map →
рекомендации курсов и стажировок → анализ резюме.

- **Базовый URL** (локально): `http://localhost:8000`
- **Интерактивная документация**: `/docs` (Swagger UI)
- **OpenAPI-спецификация**: `/openapi.json`

---

## Общие сведения

### CORS

API разрешает кросс-доменные запросы из браузера. Настройка —
`CORS_ORIGINS` в окружении: список origins через запятую, `*` — разрешить все
(значение по умолчанию).

### Формат ошибок

Ошибки приложения возвращаются в JSON:

```json
{ "detail": "Описание ошибки" }
```

| Код | Когда |
|-----|-------|
| `404 Not Found` | ресурс не найден (пользователь, миссия, роль и т.д.); анализ ещё не выполнен |
| `422 Unprocessable Entity` | некорректные входные данные |
| `409 Conflict` | конфликт данных (например, дубликат) |

Ошибки валидации pydantic возвращаются стандартным для FastAPI форматом
(`422` со списком `detail`).

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

## Полный сценарий

```bash
BASE=http://localhost:8000

# 1. Создание пользователя
curl -s -X POST $BASE/users -H "Content-Type: application/json" \
  -d '{"name":"Студент","direction":"backend"}'

# 2. Выбор целевой роли
curl -s -X PUT $BASE/users/1/goal -H "Content-Type: application/json" \
  -d '{"target_role_id":1}'

# 3. Диагностика (банк вопросов → ответы → Skill Map)
curl -s "$BASE/assessment/questions?user_id=1"
curl -s -X POST $BASE/users/1/assessment -H "Content-Type: application/json" \
  -d '{"answers":[{"question_id":1,"option_index":2}]}'

# 4. Миссия строго по цели → ответ → результат
curl -s "$BASE/missions/next?user_id=1"
curl -s -X POST $BASE/missions/4/answer -H "Content-Type: application/json" \
  -d '{"user_id":1,"option_id":7}'

# 5. Прогресс и рекомендации
curl -s $BASE/users/1/progress
curl -s "$BASE/courses/recommended?user_id=1"
curl -s "$BASE/internships/recommended?user_id=1"

# 6. Резюме и анализ
curl -s -X POST $BASE/users/1/resumes -H "Content-Type: application/json" \
  -d '{"text":"Python, SQL. Образование: МГТУ."}'
curl -s -X POST $BASE/resumes/1/analyze
curl -s $BASE/resumes/1/analysis
```