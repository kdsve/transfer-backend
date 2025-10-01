from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from .config import settings
from .db import init_db, get_session
from .models import Transfer, VehicleClass
from .schemas import TransferCreate, TransferRead
from .security import verify_telegram_init_data  # твоя функция валидации initData
from .telegram_forwarder import forward_transfer_message

app = FastAPI(title="Transfer API")

# CORS (нужен только для тестов в браузере вне Telegram)
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["POST", "OPTIONS", "GET"],
        allow_headers=["*"],
    )


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/")
def root():
    return {"ok": True, "service": "transfer-api"}


@app.get("/health")
def health():
    return "ok"


def validate_capacity(vehicle_class: VehicleClass, pax: int) -> None:
    # minivan <= 6, остальные <= 3
    cap = 6 if vehicle_class == VehicleClass.minivan else 3
    if pax > cap:
        raise HTTPException(
            status_code=422,
            detail=f"Для класса {vehicle_class} максимум {cap} пассажиров.",
        )


def validate_datetime(dt: datetime) -> None:
    # не раньше чем через 30 минут от текущего UTC
    min_dt = datetime.utcnow() + timedelta(minutes=30)
    if dt < min_dt:
        raise HTTPException(
            status_code=422,
            detail="Дата/время должны быть не раньше чем через 30 минут.",
        )


@app.post("/transfers", response_model=TransferRead, status_code=201)
async def create_transfer(
    data: TransferCreate,
    request: Request,
    session: Session = Depends(get_session),
    # Принимаем ОБА варианта заголовка:
    x_init_1: str | None = Header(None, alias="X-Telegram-InitData"),
    x_init_2: str | None = Header(None, alias="X-Telegram-Init-Data"),
):
    # Берём initData: заголовок (любой из двух) либо поле в теле как фолбэк
    init_data = (x_init_1 or x_init_2 or data.telegram_init_data or "").strip()

    # Если BOT_TOKEN задан, включаем строгую проверку initData
    if settings.BOT_TOKEN:
        if not init_data or not verify_telegram_init_data(init_data):
            raise HTTPException(status_code=401, detail="Invalid Telegram init data")

    # Бизнес-валидации
    validate_capacity(data.vehicle_class, data.pax_count)
    validate_datetime(data.datetime)

    # Сохранение
    transfer = Transfer(
        departure_city=data.departure_city,
        departure_address=data.departure_address,
        arrival_city=data.arrival_city,
        arrival_address=data.arrival_address,
        datetime=data.datetime,
        vehicle_class=data.vehicle_class,
        pax_count=data.pax_count,
        luggage=data.luggage,
        child_seat=data.child_seat,
        contact_phone=data.contact_phone,
        contact_method=data.contact_method,
        comment=(data.comment or "").strip()[:300] or None,
        telegram_init_data=init_data[:4000],
    )
    session.add(transfer)
    session.commit()
    session.refresh(transfer)

    # Уведомление во второй бот/чат (best-effort)
    text = (
        "<b>Новая заявка на трансфер</b>\n"
        f"🗓 <b>Когда:</b> {data.datetime.isoformat()}\n"
        f"🚗 <b>Класс:</b> {data.vehicle_class}\n"
        f"👥 <b>Пассажиров:</b> {data.pax_count}  "
        f"{'📦 багаж ' if data.luggage else ''}{'👶 кресло ' if data.child_seat else ''}\n"
        f"📍 <b>Откуда:</b> {data.departure_city}, {data.departure_address}\n"
        f"🏁 <b>Куда:</b> {data.arrival_city}, {data.arrival_address}\n"
        f"☎️ <b>Контакт:</b> {data.contact_phone} ({data.contact_method})\n"
        + (f"📝 <b>Комментарий:</b> {data.comment}\n" if data.comment else "")
        + f"🆔 <code>{transfer.id}</code>"
    )
    try:
        await forward_transfer_message(text)
    except Exception:
        # не падаем, если пересылка недоступна
        pass

    return TransferRead(id=transfer.id, status="accepted")
