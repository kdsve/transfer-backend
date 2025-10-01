from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session
from datetime import datetime, timedelta
from .config import settings
from .db import init_db, get_session
from .schemas import TransferCreate, TransferRead
from .models import Transfer, VehicleClass
from .security import verify_telegram_init_data
from .telegram_forwarder import forward_transfer_message

app = FastAPI(title="Transfer API")

# CORS (only needed when testing the WebApp outside Telegram)
origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["POST", "OPTIONS"],
        allow_headers=["*"],
    )

@app.on_event("startup")
def on_startup():
    init_db()

def validate_capacity(vehicle_class: VehicleClass, pax: int):
    # UPDATED constraints: minivan <= 6, others <= 3
    cap = 6 if vehicle_class == VehicleClass.minivan else 3
    if pax > cap:
        raise HTTPException(status_code=422, detail=f"Для класса {vehicle_class} максимум {cap} пассажиров.")

def validate_datetime(dt: datetime):
    min_dt = datetime.utcnow() + timedelta(minutes=30)
    if dt < min_dt:
        raise HTTPException(status_code=422, detail="Дата/время должны быть не раньше чем через 30 минут.")

@app.post("/transfers", response_model=TransferRead, status_code=201)
async def create_transfer(
    data: TransferCreate,
    session: Session = Depends(get_session),
    x_telegram_initdata: str | None = Header(None),
):
    init_data = data.telegram_init_data or (x_telegram_initdata or "")
    if not verify_telegram_init_data(init_data):
        raise HTTPException(status_code=401, detail="Invalid Telegram init data")

    validate_capacity(data.vehicle_class, data.pax_count)
    validate_datetime(data.datetime)

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
        pass

    return TransferRead(id=transfer.id, status="accepted")
