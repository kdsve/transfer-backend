# Transfer Backend (FastAPI + PostgreSQL)

Минимальный бэкенд под твой Telegram Mini App для сбора заявок на трансферы.

## Особенности
- FastAPI + SQLModel
- PostgreSQL (по умолчанию), можно SQLite для локала
- Проверка `telegram_init_data` (в dev можно отключить, не задавая `BOT_TOKEN`)
- Пересылка созданной заявки во второй бот/чат (через `FORWARD_BOT_TOKEN` и `FORWARD_CHAT_ID`)
- Бизнес-правила вместимости: **minivan ≤ 6, остальные классы ≤ 3**

## Быстрый старт (локально, без Docker)
1. Python 3.11+
2. Установи зависимости:
   ```bash
   pip install -r requirements.txt
   ```
3. Скопируй `.env`:
   ```bash
   cp .env.example .env
   ```
4. Укажи `DATABASE_URL`. Пример для SQLite (в одном файле, без внешней БД):
   ```env
   DATABASE_URL=sqlite:///./transfer.db
   ```
   > Для SQLite нужно поменять строку в `app/db.py` на:
   > ```python
   > engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
   > ```
   > (или добавь условие if 'sqlite' in DATABASE_URL)
5. Запусти API:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

## Docker (локально/прод)
```bash
cp .env.example .env
docker compose up -d --build
```

## Эндпоинт
`POST /transfers` → `201` и JSON с `id`.

## Проверка (curl)
```bash
curl -X POST http://localhost:8000/transfers   -H "Content-Type: application/json"   -d '{
    "departure_city":"Москва",
    "departure_address":"Шереметьево, Т2",
    "arrival_city":"Москва",
    "arrival_address":"Тверская, 7",
    "datetime":"2025-10-02T14:30:00+03:00",
    "vehicle_class":"minivan",
    "pax_count":6,
    "luggage":true,
    "child_seat":false,
    "contact_phone":"+79991234567",
    "contact_method":"telegram",
    "comment":"Встреча у выхода B",
    "telegram_init_data":"hash=dev"
  }'
```

## Важное
- В проде обязательно задай `BOT_TOKEN` для проверки подписи `initData`.
- На фронте используй те же ключи payload.
- Если фронт не в Telegram (тесты), пропиши CORS в `.env` (`CORS_ORIGINS`).

## Лимиты пассажиров
- `minivan` → максимум **6**
- `standard`, `comfort`, `business` → максимум **3**

Если нужно расширить логику (детские кресла влияют на вместимость, багаж и т.д.) — пиши, добавим правила.
