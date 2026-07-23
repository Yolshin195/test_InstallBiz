# File Stats Service

Сервис скачивает каталог текстовых файлов через внешнее тестовое API и считает
статистику встречаемости цифр 0-9 в содержимом файлов. Построен по гексагональной
архитектуре (ports & adapters).

## Архитектура

```
src/app/
  domain/            — сущности, доменные исключения, порты (Protocol) — без внешних зависимостей
    entities.py
    exceptions.py
    ports/
      file_catalog_client.py   # порт: общение с внешним API
      file_repository.py       # порт: хранение файлов
      progress_store.py        # порт: прогресс скачивания (Redis)
      task_dispatcher.py       # порт: запуск фоновой задачи (Celery)

  application/use_cases/       — бизнес-логика (не знает о FastAPI/Celery/SQLAlchemy)
    download_catalog.py        # весь цикл скачивания каталога, ретраи по 429/403
    start_download.py          # создать сессию и поставить задачу в очередь
    get_progress.py            # чтение прогресса (снапшот + поток для SSE)
    list_downloaded_files.py   # пагинированный список файлов
    compute_statistics.py      # расчёт статистики по цифрам

  adapters/
    inbound/
      http/                    # FastAPI: HTML-страницы (htmx) + JSON API + SSE
      celery_tasks/tasks.py     # Celery-задача — тонкая обёртка над DownloadCatalogUseCase
    outbound/
      external_api/            # httpx-клиент внешнего API + самоограничение частоты (pyrate-limiter)
      persistence/              # Advanced Alchemy: модель + репозиторий (Postgres)
      redis/                    # хранилище прогресса в Redis (+ pub/sub для SSE)
      celery/                   # адаптер порта task_dispatcher поверх Celery

  di.py            — Dishka-провайдеры, связывающие порты с адаптерами
  main.py          — FastAPI app factory
  celery_app.py    — экземпляр Celery
  config.py        — настройки (pydantic-settings)
  logging_config.py
```

Ключевой принцип: **Celery-задача не содержит бизнес-логики** — она лишь строит
DI-контейнер на процесс воркера и вызывает `DownloadCatalogUseCase.execute()`.
Вся логика (пагинация по 3 файла, ретраи при 429/403 с учётом `Retry-After`,
дедупликация уже скачанного, обновление прогресса) — в `application/use_cases/`.

## Как это работает

1. Пользователь жмёт «Скачать данные» → `StartDownloadUseCase` создаёт `session_id`,
   публикует начальный прогресс в Redis и ставит Celery-задачу `download_catalog`.
2. Воркер выполняет `DownloadCatalogUseCase.execute(session_id)`:
   `GET /api/files/names` → `POST /api/files/download` (пачками по 3) →
   сохранение в Postgres → `POST /api/files/downloaded` → обновление прогресса
   в Redis — пока `names` не вернёт пустой список.
3. Браузер подписан на `GET /download/progress/stream/{session_id}` (SSE, htmx
   `sse` extension) — эндпоинт слушает Redis pub/sub и рендерит HTML-фрагмент
   на каждое обновление прогресса.
4. Страница `/files` — пагинированный список скачанных файлов с выбором
   (точечно / все на странице / вообще все) и кнопкой «Произвести расчёты»,
   которая считает статистику по цифрам (общую и по каждому файлу).

## Запуск через Docker Compose

```bash
cp .env.example .env
# отредактируйте EXTERNAL_API_BASE_URL и EXTERNAL_API_CANDIDATE_ID в .env
docker compose up --build
```

Сервис поднимет Postgres, Redis, прогонит миграции Alembic (сервис `migrate`),
затем запустит `web` (http://localhost:8000) и `worker` (Celery).

Откройте http://localhost:8000/download.

## Локальный запуск без Docker

```bash
uv sync
cp .env.example .env  # укажите POSTGRES_HOST=localhost, REDIS_HOST=localhost и т.д.

# поднимите Postgres и Redis локально (например, через docker compose up postgres redis)

uv run alembic upgrade head
uv run uvicorn app.main:create_app --factory --reload --app-dir src

# в отдельном терминале:
uv run celery -A app.celery_app.celery_app worker --loglevel=INFO
```

## Переменные окружения

См. `.env.example`. Главное:
- `EXTERNAL_API_BASE_URL` — базовый URL тестового API каталога файлов.
- `EXTERNAL_API_CANDIDATE_ID` — необязательный `X-Candidate-Id`; если не задан,
  сервис идентифицируется по IP (как описано в ТЗ).
- `EXTERNAL_API_RATE_LIMIT_PER_SECOND` — самоограничение частоты запросов
  к внешнему API (проактивно, до получения 429).
- `DISPLAY_TZ` — таймзона для отображения времени старта скачивания (по
  умолчанию `Asia/Novosibirsk`, как требует ТЗ).

## Что проверено локально (в sandbox без реальных Postgres/Redis/внешнего API)

- Все модули компилируются и импортируются (`py_compile`, прямой импорт каждого слоя).
- Граф зависимостей Dishka собирается без ошибок (`make_async_container`).
- Celery-приложение поднимается, задача `download_catalog` регистрируется.
- FastAPI-приложение собирается, роуты `/download`, `/files`, `/api/progress/...`
  матчатся через `TestClient`; страница `/download` рендерится и отдаёт HTML с htmx+SSE.
- Обращение к `/files` без поднятого Postgres падает ожидаемо на этапе
  подключения к БД (`ConnectionRefusedError`) — то есть DI-цепочка до слоя
  персистентности работает корректно, ошибка ровно там, где и должна быть.

Что стоит сделать перед боевым использованием: прогнать `docker compose up`
целиком против реального тестового API, проверить полный цикл скачивания
на настоящих данных и посмотреть логи на предмет неожиданных кодов ошибок API.
