# Архитектура

Понять систему за 10 минут: кто с кем говорит, где что хранится и где
проходит граница ответственности.

---

## 1. Общая схема

```mermaid
flowchart LR
    subgraph user["Пользователь"]
        MAX["Мессенджер MAX"]
    end

    subgraph edge["Периметр"]
        Caddy["Caddy<br/>TLS, заголовки, лимит 2MB"]
    end

    subgraph app["Контейнеры"]
        Bot["MAX-бот<br/>polling MAX"]
        API["FastAPI<br/>:8000"]
    end

    subgraph data["Данные"]
        DB[("SQLite<br/>skillquest.db")]
        Giga["GigaChat<br/>внешний сервис"]
    end

    MAX <-->|"HTTPS"| Caddy
    MAX <-->|"polling + webhook событий"| Bot
    Bot -->|"HTTP + Bearer service"| API
    Caddy -->|"reverse_proxy"| API
    API --> DB
    API -->|"если включено,<br/>текст резюме"| Giga

    style Giga stroke-dasharray: 5 5
    style DB fill:#e8f0fe
```

Две входные точки:

- **Caddy** — для человека и внешних клиентов, единственная точка с TLS.
  Порт `8000` наружу не публикуется.
- **Бот** — длинный опрос (`polling`) событий MAX. Работает по
  внутренней сети Docker, в HTTPS не нуждается.

---

## 2. Слои

### Бот (`bot/`)

| Модуль | Ответственность |
|---|---|
| `main.py` | токен, диспетчер, роутеры, обработчик ошибок, polling |
| `handlers/` | экраны: цель, диагностика, миссия, Skill Map, резюме, рекомендации |
| `keyboards.py` | все клавиатуры и payload'ы кнопок |
| `texts.py` | весь текст, который видит пользователь |
| `sessions.py` | состояние диалога в памяти процесса |
| `api.py` | HTTP-клиент к API, единый путь Bearer-токена |

Бот **не решает** доменных задач: он не считает XP, не выбирает миссию и
не разбирает резюме. Он показывает экраны, собирает нажатия и зовёт API.

### API (`backend/`)

| Слой | Ответственность |
|---|---|
| `api/routes/` | HTTP: разбор запроса, коды ответов, OpenAPI |
| `api/deps.py` | аутентификация и авторизация: роли, владение, `401`/`403` |
| `schemas/` | pydantic-модели запросов и ответов |
| `services/` | правила игры: миссии, навыки, gap-анализ, рекомендации, анализ резюме |
| `repositories/` | доступ к данным, доменные ошибки `404` |
| `domain/` | модели SQLAlchemy |
| `database/` | движок, сессии, агрегация моделей |
| `core/` | настройки, шифрование, аудит, согласие, исключения |

### Слой шифрования

Включён в ORM, а не в роутеры, поэтому его нельзя обойти случайно:

```mermaid
flowchart TB
    Route["POST /users/1/resumes<br/>роут"] --> Schema["ResumeCreate<br/>схема"]
    Schema --> Repo["ResumeRepository.create"]
    Repo --> ORM["Resume.text<br/>EncryptedText"]
    ORM --> Enc["encrypt()<br/>Fernet"]
    Enc --> DB[("БД: enc:v1:...")]

    DB --> Dec["decrypt()"]
    Dec --> Read["чтение в ORM"]
    Read --> Out["ResumeOut<br/>схема ответа"]
    Out --> Route
```

`EncryptedString` / `EncryptedText` — `TypeDecorator` над `String`/`Text`:
шифруют в `process_bind_param`, расшифровывают в `process_result_value`.
Длина колонки увеличивается автоматически. Значения, записанные до
включения шифрования, не имеют префикса `enc:v1:` и читаются как есть.

Токены — отдельная история: в `api_tokens` лежит только SHA-256, они не
шифруются, а хэшируются, и при каждом запросе хэш пришедшего токена
ищется в таблице.

---

## 3. Ответ на миссию

```mermaid
sequenceDiagram
    autonumber
    actor U as Пользователь
    participant B as Бот
    participant A as API
    participant D as SQLite

    U->>B: 🎮 «Миссия»
    B->>A: GET /missions/next?user_id=N
    A->>A: require_access: student == владелец?
    A->>D: пользователь, требования роли, навыки, попытки
    D-->>A: строки
    A->>A: приоритет: пробел → mandatory → gap×importance → не пробована → сложность → id
    A-->>B: status ok, mission, варианты
    B->>B: сдвиг вариантов: offset = id % (n−1) + 1
    B-->>U: сценарий + пронумерованные варианты + кнопки ①②③④

    U->>B: нажатие «③»
    B->>A: POST /missions/7/answer {user_id, option_id}
    A->>A: require_access + сверка user_id
    A->>D: вариант, прошлые верные попытки
    D-->>A: is_correct, previous attempt?

    alt уже решено верно
        A->>D: ничего не пишем
        A-->>B: already_solved true, xp_earned 0
    else первый раз
        A->>D: XP = reward_xp + бонус сложности
        A->>D: обновить user_skills.level/experience
        A->>D: вставить attempts
        A->>D: COMMIT
        A-->>B: is_correct, xp_earned, уровень до/после
    end

    B-->>U: ✅ Верно! +20 XP, уровень 1 → 2, объяснение
```

Ключевое: обновление навыка и запись попытки идут **одной
транзакцией** (`commit=False` у обоих, `commit` делает сервис). Полученный
опыт не может «потеряться» или задваиться.

---

## 4. Границы ответственности

| Вопрос | Владелец |
|---|---|
| Какую кнопку показать дальше | бот |
| Как перевести payload в действие | бот |
| Может ли пользователь читать чужие данные | API |
| Какая миссия следующая | API |
| Сколько XP и какой уровень | API |
| Что найдено в резюме | API |
| Есть ли согласие на обработку | бот спрашивает, API хранит |
| Где лежат данные | API |

Правило: **бот не доверяет вводу пользователя**. `user_id` в теле
запроса сверяется с владельцем токена на стороне API
(`require_access`, `require_resume_owner`, `require_attempt_owner`).
Подмена `user_id` в теле даёт `403`, а не тихую запись чужим данным.

Правило: **API не знает про мессенджер**. У него нет представления о
кнопках, экранах и форматировании текста. Единственное исключение —
`POST /users/by-max`, связывающий `max_user_id` с профилем; он же
единственная операция, закрытая ролью `service`.

---

## 5. Где живёт состояние

| Состояние | Где | Что теряется |
|---|---|---|
| Профиль, цели, согласие | `users` | ничего |
| Skill Map, XP, попытки | `user_skills`, `attempts` | ничего |
| Резюме и разбор | `resumes`, `resume_analysis` | ничего |
| Токены, роли | `api_tokens` | ничего |
| Каталог контента | `skills`, `missions`, `roles`, `courses`, `internships` | ничего |
| **Диалог: `uid`, ответы диагностики, флаги резюме и согласия** | **память процесса бота** | **сбрасывается при рестарте бота** |
| Токен доступа бота | `api.py`, из переменной окружения | перечитывается при старте |
| HTTP-пул | `api._client` | пересоздаётся |

Сессии бота — `bot/sessions.py`, обычный словарь в памяти:

```python
sessions[max_user_id] = {
    "uid": None,       # id профиля на платформе
    "answers": [],     # ответы текущей диагностики
    "resume": False,   # ждём резюме
    "welcomed": False, # приветствие уже отправлено
    "consent": False,  # согласие на обработку ПД выдано
}
```

`uid` кэшируется, чтобы не делать `POST /users/by-max` на каждое
нажатие. Согласие **дублируется** в `users.consent_given`: в БД оно
живёт постоянно, в памяти — до перезапуска. После рестарта бот задаст
вопрос заново, что соответствует требованию явного согласия.

Ограничение сразу видно: два инстанса бота не разделяют состояние, и
перезапуск обрывает начатую диагностику. Перенёс состояния — замена
`bot/sessions.py` на FSM `maxapi.context.StateContext` с Redis-хранилищем
либо на чтение из БД; ключи сессии и точки вызова `sessions.*` при этом
не меняются.

---

## 6. Интеграции

### GigaChat

Выключена по умолчанию. Включается `GIGACHAT_CREDENTIALS` или
`GIGACHAT_ACCESS_TOKEN`.

```mermaid
sequenceDiagram
    participant A as API
    participant G as GigaChat

    A->>A: оценивают только новые резюме
    A->>G: POST /chat/completions<br/>system + prompt (резюме ≤ 8000 символов)
    G-->>A: JSON {score, summary, strengths, issues, recommendations}
    A->>A: парсинг, отсечение списков
    A->>A: source = "gigachat", ai_score, ai_summary
```

Пока ключа нет, `GigaChatClient.configured` возвращает `False`, и разбор
остаётся эвристическим — отчёт помечается `source: "heuristic"`.
Любая ошибка сети или формата ловится и деградирует до эвристики:
неисправность внешнего сервиса не ломает разбор.

Что уходит наружу: текст резюме, найденные навыки, выбранное
направление. Это передача третьему лицу, раскрытая в политике и в
согласии — подробно в [PRIVACY.md](PRIVACY.md#4-передача-третьим-лицам).

### MAX

Библиотека `maxapi`: события (`bot_started`, `message_created`,
`message_callback`), `send_message`, `edit`, `download_bytes`, polling.
Ограничения площадки и карта экранов — в [BOT.md](BOT.md).

---

## 7. Поток данных персональных данных

```mermaid
flowchart LR
    U["Пользователь"] -->|"имя, MAX-id"| B["Бот"]
    B -->|"service-токен"| A["API"]
    U -->|"согласие, резюме"| B
    B --> A
    A -->|"Fernet"| DB[("SQLite")]
    A -->|"резюме ≤ 8000 символов"| G["GigaChat"]
    A -.->|"AUDIT: факт, роль, id, без значений"| L["Журнал"]
```

Шифрование покрывает ПД в покое, TLS — в пути, аудит — доступ.
Подробно в [PRIVACY.md](PRIVACY.md).
