# Модель безопасности SkillQuest

Как устроена защита: роли и границы доступа, хранение и ротация секретов,
аудит и порядок работы с ним. Обработка персональных данных описана
отдельно в [PRIVACY.md](PRIVACY.md).

Короткий `SECURITY.md` в корне репозитория — политика раскрытия
уязвимостей, он же виден кнопкой Security на GitHub.

---

## 1. Модель угроз

| Угроза | Мера |
|---|---|
| Чужой читает данные пользователя | разграничение по ролям, проверка владения в зависимостях FastAPI, `403` на чужой `user_id` |
| Подбор токена перебором | токены — случайные 32 байта (`secrets.token_urlsafe`), в БД только SHA-256, сравнение сервисного токена постоянного времени |
| Доступ без токена | `401` на любой защищённой операции, `security` в OpenAPI |
| Чтение базы или бэкапа | шифрование полей ПД Fernet, токены — хэшами |
| Перехват трафика | единственный вход — Caddy с TLS, порт 8000 наружу не публикуется |
| Веб-атаки с чужого origin | `CORS_ORIGINS` по умолчанию пуст, заголовки `nosniff` / `DENY` / `no-referrer` |
| Злоупотребление ботом | роль `service` — только `POST /users/by-max` и операции с данными, всё под токеном |
| Незаметный доступ к ПД | журнал аудита `AUDIT:` без значений полей |
| Обработка ПД без согласия | экран согласия перед приёмом резюме, фиксация в БД, fail closed |

Вне модели: физический доступ к серверу, компрометация хоста, DoS и
недоступность — отдельная эксплуатационная тема.

---

## 2. Роли

Роль определяется токеном, а не заголовком: `get_optional_principal`
ищет `ApiToken` по SHA-256 хэшу значения `Authorization: Bearer …`, иначе
сравнивает с `SERVICE_API_TOKEN`. Дальше роль решает всё.

| Роль | Как выдаётся | Границы |
|---|---|---|
| `student` | `scripts/seed_test_accounts.py`; `user_id` токена = владелец данных | только свои ресурсы; чужой `user_id`, чужое резюме, чужая попытка → `403` |
| `service` | `SERVICE_API_TOKEN` в окружении; есть встроенное значение по умолчанию | `POST /users/by-max`, чтение любого профиля, загрузка и анализ резюме, фиксация и отзыв согласия |
| `admin` | `scripts/seed_test_accounts.py` | `POST /admin/test-users/reset`; полный доступ к ПД **не** выдан |

Реализация: `backend/app/api/deps.py`.

- `require_access(user_id, principal)` — владелец или не `student`;
- `require_resume_owner`, `require_attempt_owner` — проверка по записи;
- `require_service`, `require_admin` — только своя роль.

Границы на уровне зависимостей, а не в коде роутов: забыть проверку в
одном роутере нельзя, не вызвав зависимость явно.

### Что сервисная роль может НЕ

- создать пользователя с чужим `id` — только get-or-create по `max_user_id`;
- обойти шифрование — данные читаются и пишутся только через ORM.

---

## 3. Токены доступа

### Где хранятся

В `api_tokens` лежит **только** SHA-256 хэш: `token_hash`, `role`,
`user_id`, `is_test`, `created_at`. Открытый текст не сохраняется и
печатается один раз при создании.

Следствие: утечка дампа таблицы не даёт готовых токенов, но и восстановить
токен нельзя — при утрате учётку создают заново.

### Ротация

| Токен | Как ротировать |
|---|---|
| `student`, `admin` | `python scripts/seed_test_accounts.py --reset` — учётки и токены пересоздаются, прежние перестают работать |
| `service` (`SERVICE_API_TOKEN`) | сменить переменную и перезапустить **оба** сервиса: compose передаёт боту `SKILLQUEST_API_TOKEN=${SERVICE_API_TOKEN}`, поэтому рассинхрон даёт `401` на `POST /users/by-max`, и кнопки «Цель», «Диагностика», «Миссия», «Skill Map» перестают работать |
| `DATA_ENCRYPTION_KEY` | см. [раздел 4](#4-ключ-шифрования-пд) |

Проверка после ротации:

```bash
docker inspect skillquest-bot --format '{{range .Config.Env}}{{println .}}{{end}}' \
  | grep SKILLQUEST_API_TOKEN
```

Значение в контейнере бота должно совпадать с `SERVICE_API_TOKEN`
у backend.

### Случайная строка

Если задаёте свой `SERVICE_API_TOKEN` — не оставляйте встроенное
`skillquest-service-token`: оно опубликовано в репозитории.

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 4. Ключ шифрования ПД

`DATA_ENCRYPTION_KEY` — Fernet, base64url, 32 байта.

```bash
cd backend && python -m backend.app.core.encryption
```

Поведение при отсутствии ключа:

| `APP_ENV` | Поведение |
|---|---|
| `production` | **не стартует** — `RuntimeError` при импорте настроек |
| любой, но ключ битый | не стартует, `RuntimeError` с указанием формата |
| `development`, `testing` | временный ключ процесса + предупреждение в лог: данные не переживут перезапуск |

В compose ключ обязателен (`:?`), поэтому `docker compose up` падает
сразу, если переменной нет. Молчаливого режима «хранить в открытом
виде» не существует.

### Что покрыто и что нет

Зашифрованы `users.name`, `users.education`, `users.direction`,
`users.goal`, `resumes.text`, `resumes.filename`. Не зашифрованы `id`,
`max_user_id`, числовые показатели прогресса и даты — по ним нужны
индексы и агрегация. Подробности и обоснование — в
[PRIVACY.md](PRIVACY.md#2-что-зашифровано).

### Ротация ключа

Смена ключа делает существующие шифротексты нечитаемыми: `decrypt`
поднимает `ValueError`. Порядок:

1. **Сначала бэкап.** `DATA_ENCRYPTION_KEY` хранится отдельно от данных.
   Потеря ключа равносильна потере расшифрованных данных.
2. Остановить запись: `docker compose stop bot backend`.
3. Перешифровать данные скриптом перебора: выбрать все строки
   `users.name/education/direction/goal` и `resumes.text/filename`,
   для каждой `decrypt` старым ключом → `encrypt` новым, обновить
   транзакцией.
4. Проверить, что счётчики совпадают и `decrypt` новым ключом читает всё.
5. Заменить `DATA_ENCRYPTION_KEY` в `.env` и в секретах окружения,
   пересоздать контейнеры: `docker compose up -d --build`.
6. Отозвать старый `SERVICE_API_TOKEN` и выпустить новый.

Операция идемпотентна только по незашифрованным строкам: значения с
префиксом `enc:v1:` перешифровываются всегда, поэтому повторный запуск
прохода безопасен, а вот пропуск строки оставляет данные нечитаемыми —
сверяйте количество строк до и после.

---

## 5. Аудит

### Что пишется

`backend/app/core/audit.py`, логгер `skillquest.audit`, префикс `AUDIT:`.

```json
{"timestamp": "2026-09-29T12:00:00+00:00", "action": "read",
 "resource": "user", "resource_id": 1, "principal_role": "student",
 "principal_user_id": 1, "details": {}}
```

`action`: `read`, `create`, `update`, `export`, `delete`, `revoke_consent`,
`admin_reset`. Значения полей в журнал не попадают.

### Кто и как проверяет

| Роль | Доступ к журналу | Как смотрит |
|---|---|---|
| `admin` | да | `docker compose logs backend \| grep AUDIT` |
| `student` | нет | журнал не отдаётся через API |
| `service` (бот) | нет, только пишет | бот не читает журнал |

Проверка:

```bash
# обращения к профилю конкретного пользователя
docker compose logs backend | grep 'AUDIT' | grep '"resource_id": 1'

# только удаления и экспорты — события высокой значимости
docker compose logs backend | grep -E '"action": "(delete|export|revoke_consent)"'

# отказоустойчиво за пределами контейнера
docker compose logs backend --no-log-prefix | grep 'AUDIT' > audit-$(date +%F).log
```

**Что искать при разборе инцидента:**

1. `principal_role: "service"` с `resource_id`, которого бот не должен
   трогать, — признак скомпрометированного `SERVICE_API_TOKEN`;
2. `admin_reset` вне окна тестирования;
3. `export` и `delete`, которые пользователь не инициировал;
4. резкий рост `create` по `resume` — вероятная загрузка данных
   в массовом объёме.

### Ротация и хранение

Журнал пишется в stdout контейнера, то есть в журнал Docker
(`json-file` driver). **Ротации Docker по умолчанию нет** — лог растёт
бесконечно. Настройте в `/etc/docker/daemon.json`:

```json
{ "log-driver": "json-file", "log-opts": { "max-size": "50m", "max-file": "10" } }
```

Получить и положить в архив:

```bash
docker inspect skillquest-backend --format '{{.LogPath}}'
```

Сроки хранения журнала аудита и его отзыв по запросу субъекта —
вопрос, который стоит закрыть до эксплуатации (см.
[PRIVACY.md](PRIVACY.md#9-известные-ограничения)).

---

## 6. Транспорт и периметр

```text
Интернет ──HTTPS──► Caddy ──внутренняя сеть──► backend:8000 ──► SQLite
                       ▲
                       └──► bot (polling к MAX, HTTP к backend)
```

- `compose.yaml` публикует только `80` и `443` на Caddy; `8000` наружу
  не выходит;
- Caddy: TLS через Let's Encrypt, `encode zstd gzip`, лимит тела `2MB`,
  заголовки `X-Content-Type-Options`, `X-Frame-Options: DENY`,
  `Referrer-Policy`, `-Server`, JSON-доступ в stdout;
- `SITE_ADDRESS` — домен для сертификата либо `:80` для локальной работы;
- `ACME_EMAIL` — адрес для уведомлений Let's Encrypt.

Локальная разработка: `SITE_ADDRESS=:80`, HTTPS выключен, Caddy
перестаёт быть TLS-терминатором — это не для прода.

---

## 7. Секреты в репозитории

| Секрет | Где | В Git |
|---|---|---|
| `MAX_BOT_TOKEN` | `.env` | нет, `.env` в `.gitignore` |
| `SERVICE_API_TOKEN` | `.env` | нет |
| `DATA_ENCRYPTION_KEY` | `.env` | нет |
| `GIGACHAT_CREDENTIALS` | `.env` | нет |
| значение по умолчанию сервисного токена | `backend/app/core/config.py` | **да** — поэтому в `production` его нужно заменить |

Перед коммитом: `git diff --cached | grep -iE 'token|key|secret'`.

---

