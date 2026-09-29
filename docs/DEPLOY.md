# DEPLOY.md — запуск и эксплуатация

Runbook: поднять с нуля, обновить, снять бэкап, восстановиться,
откатиться. Предполагается Linux-сервер с Docker и Docker Compose.

---

## 1. Требования

| | Минимум | Комфортно |
|---|---|---|
| CPU | 2 ядра | 2–4 ядра |
| RAM | 2 ГБ | 4 ГБ |
| Диск | 20 ГБ | 40 ГБ с запасом на бэкапы |
| ОС | Ubuntu 22.04 / Debian 12 с Docker 24+ и Compose v2 | любой с Docker |
| Сеть | входящие 80 и 443 | плюс SSH |

DNS: A/AAAA-запись домена на адрес сервера. Домен нужен для сертификата
Let's Encrypt — без него Caddy работает только на `:80`, и это режим
локальной разработки, а не продакшн.

Проверка перед началом:

```bash
docker --version && docker compose version
df -h / && free -h
dig +short example.com        # домен должен указывать на сервер
curl -4 ifconfig.me            # внешний адрес для сверки
```

Если сервер за NAT, порт 443 должен быть проброшен на него, иначе
ACME-челлендж не пройдёт.

---

## 2. Получение кода

```bash
sudo apt-get update && sudo apt-get install -y git
sudo mkdir -p /opt && sudo chown "$USER" /opt
git clone <репозиторий> /opt/skillquest
cd /opt/skillquest
```

---

## 3. Переменные окружения

```bash
cd /opt/skillquest
cp .env.example .env
chmod 600 .env                  # секреты читает только владелец
```

Сгенерировать секреты:

```bash
# токен сервисной роли — вместо встроенного значения по умолчанию
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# ключ шифрования персональных данных
cd backend && python -m backend.app.core.encryption && cd ..
```

Заполнить `.env`:

```env
APP_NAME=SkillQuest
APP_ENV=production
DATABASE_URL=sqlite:////app/data/skillquest.db
MAX_BOT_TOKEN=<токен бота из настроек MAX>
SERVICE_API_TOKEN=<сгенерированный токен>
DATA_ENCRYPTION_KEY=<сгенерированный ключ>

GIGACHAT_CREDENTIALS=<ключ GigaChat, если нужен AI-разбор>
GIGACHAT_ACCESS_TOKEN=
```

| Переменная | Обязательна | Комментарий |
|---|---|---|
| `APP_ENV` | да | `production` — ключ шифрования становится обязательным |
| `MAX_BOT_TOKEN` | да | без него бот не стартует |
| `SERVICE_API_TOKEN` | да | **заменить встроенное значение** — оно опубликовано в репозитории |
| `DATA_ENCRYPTION_KEY` | да | без него backend не стартует в `production` |
| `GIGACHAT_CREDENTIALS` | нет | без него разбор резюме эвристический |
| `SITE_ADDRESS` | нет | домен; по умолчанию `:80` — только для локальной работы |
| `ACME_EMAIL` | нет | адрес для уведомлений Let's Encrypt |
| `CORS_ORIGINS` | нет | по умолчанию пусто; боту не нужен |

`.env` не коммитится и не попадает в образы. Проверить:

```bash
git check-ignore -v .env && echo "игнорируется"
```

**`DATA_ENCRYPTION_KEY` хранить отдельно от сервера.** Потеря ключа
означает потерю расшифрованных данных — см. раздел 7.

---

## 4. Запуск

```bash
cd /opt/skillquest
docker compose up -d --build
docker compose ps
```

Ожидается три сервиса: `backend` (healthy), `bot`, `caddy`.

Первый запуск занимает несколько минут: сборка образов, выпуск
сертификата, миграции, наполнение демо-данными.

Смотреть запуск:

```bash
docker compose logs -f backend
```

В журнале ожидается:

```text
[entrypoint] Applying database migrations...
[entrypoint] Migrations applied.
[entrypoint] Starting API server on :8000...
```

---

## 5. Домен и HTTPS

Задать в `.env` и пересоздать Caddy:

```env
SITE_ADDRESS=api.example.com
ACME_EMAIL=dev@example.com
```

```bash
docker compose up -d caddy
docker compose logs -f caddy
```

Caddy сам выпустит и будет продлевать сертификат. Проверка:

```bash
curl -sSf https://api.example.com/health
curl -sSf -o /dev/null -w '%{http_code}\n' https://api.example.com/docs   # 200
```

Ошибки ACME:

| Симптом | Причина |
|---|---|
| `could not solve challenge` | порт 443 закрыт или A-запись неверная |
| `certificate obtain failed` | `SITE_ADDRESS` указывает на `localhost` или IP |
| сертификат не продлевается | контейнер Caddy перезапущен с потерей тома |

Тома `caddy_data` и `caddy_config` хранят сертификаты. Их удаление
приведёт к повторному выпуску — это безопасно, но нужно время на
проверку DNS.

---

## 6. Миграции и демо-данные

Миграции применяются **автоматически** при старте контейнера
(`backend/entrypoint.sh`). Вручную:

```bash
cd /opt/skillquest
docker compose exec -T backend alembic -c backend/alembic.ini history
docker compose exec -T backend alembic -c backend/alembic.ini current
docker compose exec -T backend alembic -c backend/alembic.ini upgrade head
```

Если миграция не применилась, entrypoint пишет предупреждение и
продолжает работу через `create_all` — схема останется старой, и
ошибка проявится позже. Поэтому состояние стоит проверять явно.

Откат миграции:

```bash
docker compose exec -T backend alembic -c backend/alembic.ini downgrade -1
```

**Перед откатом — бэкап:** `downgrade` меняет схему и может удалить
данные.

Демо-данные (навыки, миссии, курсы, стажировки, роли) наполняются при
первом старте и **не обновляются** повторно. Правила ведения контента —
в [CONTENT.md](CONTENT.md).

> Повторный вызов сида обнуляет цены всех платных курсов. Не запускать
> на боевой базе без нужды.

Тестовые учётки для приёмки API:

```bash
docker compose exec -T backend python -X utf8 scripts/seed_test_accounts.py
```

Скрипт печатает токены **один раз** — сохраните их: в базе лежит только
SHA-256, восстановить токен нельзя. Повторный прогон требует `--reset`.

---

## 7. Бэкап

### Что сохранять

| Объект | Где | Критичность |
|---|---|---|
| база данных | том `skillquest_data`, файл `/app/data/skillquest.db` | **критично** |
| `DATA_ENCRYPTION_KEY` | `.env` на сервере **и** отдельно | **критично**, без него база бесполезна |
| `SERVICE_API_TOKEN`, `MAX_BOT_TOKEN` | `.env` | высокая |
| сертификаты Caddy | томы `caddy_data`, `caddy_config` | низкая, перевыпускаются |

**База без ключа — это шифротекст.** Ключ и база должны храниться в
разных местах: утрата сервера не должна означать утрату данных.

### Скрипт бэкапа

```bash
#!/usr/bin/env bash
# /opt/skillquest/backup.sh
set -euo pipefail

DEST=/var/backups/skillquest
STAMP=$(date +%Y%m%d-%H%M%S)
mkdir -p "$DEST"

# Согласованный снимок: WAL-файлы копируются вместе с базой
docker compose exec -T backend python -X utf8 -c "
import sqlite3
src = sqlite3.connect('/app/data/skillquest.db')
dst = sqlite3.connect('/app/data/backup.db')
src.backup(dst)
dst.close(); src.close()
"

docker compose cp backend:/app/data/backup.db "$DEST/db-$STAMP.sqlite"
docker compose exec -T backend rm -f /app/data/backup.db

# Ключ шифрования — отдельно от данных
grep '^DATA_ENCRYPTION_KEY=' .env | cut -d= -f2 > "$DEST/key-$STAMP.txt"
chmod 600 "$DEST/key-$STAMP.txt"

# Проверка целостности
sqlite3 "$DEST/db-$STAMP.sqlite" "PRAGMA integrity_check;" | grep -q '^ok$' \
  && echo "$STAMP ok" || { echo "$STAMP ПОВРЕЖДЕНА"; exit 1; }

find "$DEST" -name 'db-*.sqlite' -mtime +30 -delete
find "$DEST" -name 'key-*.txt'    -mtime +30 -delete
```

```bash
chmod +x /opt/skillquest/backup.sh
echo "17 3 * * * /opt/skillquest/backup.sh >> /var/log/skillquest-backup.log 2>&1" \
  | crontab -
```

Копии базы и ключа унесите с сервера: бэкап рядом с исходными данными
не защищает от потери сервера.

---

## 8. Восстановление

```bash
cd /opt/skillquest
docker compose down

docker volume rm skillquest_data
docker volume create skillquest_data

docker run --rm -v skillquest_data:/data -v /var/backups/skillquest:/backup \
  alpine cp /backup/db-20260930-030000.sqlite /data/skillquest.db

# ключ обязан совпадать с тем, под которым шифровались данные
docker compose up -d --build
docker compose ps
curl -sSf https://api.example.com/health
```

Проверить, что данные читаются, а не расшифровываются в мусор:

```bash
docker compose logs backend | grep -i 'расшифровать'   # пусто — хорошо
```

Непустой вывод означает неверный `DATA_ENCRYPTION_KEY`. Верните
правильный: расшифровка без него невозможна.

---

## 9. Обновление версии

```bash
cd /opt/skillquest
/opt/skillquest/backup.sh
git fetch --tags
git log --oneline HEAD..origin/main
git checkout <тег>
docker compose up -d --build
```

EntryPoint сам применит миграции. Проверьте результат:

```bash
docker compose ps
docker compose exec -T backend alembic -c backend/alembic.ini current
curl -sSf https://api.example.com/health
```

Если в обновлении изменился `.env.example` — сверьте со своим `.env` и
добавьте новые переменные.

### Откат версии

```bash
cd /opt/skillquest
docker compose down
git checkout <предыдущий тег>
docker compose up -d --build
```

**Откат кода не откатывает схему.** Если новая версия добавила
миграцию, старая может не работать с новой схемой. Порядок:

1. снять бэкап **до** обновления;
2. при несовместимости — `alembic downgrade` до предыдущей ревизии;
3. если downgrade невозможен — восстановить базу из бэкапа;
4. проверить, что версия миграции совпадает с кодом:
   `alembic current`.

---

## 10. Здоровье и логи

### Проверка

```bash
docker compose ps                                   # все Up
curl -sSf https://api.example.com/health
curl -sSf -o /dev/null -w '%{http_code}\n' https://api.example.com/docs
```

`/health` отвечает `{"status":"ok","app":"SkillQuest","env":"production"}`.
В Docker HEALTHCHECK — `GET /health` каждые 30 с, три подряд неудачи
помечают контейнер как unhealthy; `bot` и `caddy` ждут его готовности.

### Логи

```bash
docker compose logs -f backend
docker compose logs -f bot
docker compose logs --since 1h backend
docker compose ps --format '{{.Service}} {{.Status}}'
```

Caddy пишет JSON-доступ в stdout. Ротации Docker по умолчанию нет —
лог растёт бесконечно. Настроить в `/etc/docker/daemon.json`:

```json
{ "log-driver": "json-file", "log-opts": { "max-size": "50m", "max-file": "10" } }
```

```bash
sudo systemctl restart docker && docker compose up -d
```

### Аудит

Журнал доступа к персональным данным, префикс `AUDIT:`:

```bash
docker compose logs backend --no-log-prefix | grep 'AUDIT' > audit-$(date +%F).log
docker compose logs backend | grep -E '"action": "(delete|export|revoke_consent)"'
```

Разбор лога — в [SECURITY.md](SECURITY.md#аудит).

---

## 11. Обслуживание

| Задача | Периодичность |
|---|---|
| проверить `backup.sh`, сверить `integrity_check` | ежедневно |
| унести копии базы и ключа с сервера | еженедельно |
| сменить `SERVICE_API_TOKEN`, перезапустить оба сервиса | каждые 90 дней |
| проверить, что сертификат продлевается | ежемесячно |
| пересобрать образы без изменения кода | при обновлении зависимостей |
| проверить актуальность ссылок каталога | раз в квартал |

Смена `SERVICE_API_TOKEN`:

```bash
sed -i "s|^SERVICE_API_TOKEN=.*|SERVICE_API_TOKEN=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')" .env
docker compose up -d --force-recreate backend bot
```

Пересоздать **оба**: иначе бот получит `401` на `POST /users/by-max` и
кнопки перестанут работать.

Смена `DATA_ENCRYPTION_KEY` требует перешифрования данных — порядок в
[SECURITY.md](SECURITY.md#ротация-ключа).

---

## 12. Диагностика

| Симптом | Проверка | Причина |
|---|---|---|
| `backend` не healthy | `docker compose logs backend` | не применены миграции, нет ключа при `production` |
| бот падает при старте | `docker compose logs bot` | не задан `MAX_BOT_TOKEN` |
| кнопки дают 401 | `docker inspect skillquest-bot --format '{{range .Config.Env}}{{println .}}{{end}}' \| grep SKILLQUEST_API_TOKEN` | бот и backend с разными `SERVICE_API_TOKEN` |
| Caddy не отвечает | `docker compose logs caddy` | `SITE_ADDRESS` пуст или 443 закрыт |
| `ValueError: не удалось расшифровать` | сверить `DATA_ENCRYPTION_KEY` с тем, что шифровало данные | смена ключа без перешифрования |
| ошибка 5xx в логах backend | `docker compose logs backend \| grep -i traceback` | сбой в сервисе |
| бот не реагирует на кнопки | `docker compose logs bot \| grep -i 'handler error'` | исключение в хендлере; опрос продолжается |
| `no such column` | `alembic upgrade head` | миграции не применены |
| место на диске кончилось | `df -h /` и `docker system df` | раздутые логи или образы |

Освобождение места:

```bash
docker system df
docker image prune -a -f
docker builder prune -f
```

`volume prune` **не** трогайте без проверки: вместе с образами он может
унести базу.

---

## 13. Полное снятие

```bash
cd /opt/skillquest
docker compose down
docker volume rm skillquest_data caddy_data caddy_config
```

Удаляет базу, резюме, согласия и токены безвозвратно. **Перед этим
убедитесь, что бэкап и `DATA_ENCRYPTION_KEY` сохранены в другом месте.**
