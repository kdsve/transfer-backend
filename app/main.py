from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import quote
from fastapi import FastAPI, Depends, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from .config import settings
from .db import init_db, get_session
from .models import Transfer, VehicleClass
from .schemas import TransferCreate, TransferRead
from .telegram_forwarder import forward_transfer_message

app = FastAPI(title="Transfer API")

# --- CORS: включаем всегда (на этапе интеграции можно оставить '*') ---
origins_str = getattr(settings, "CORS_ORIGINS", "").strip()
origins = [o.strip() for o in origins_str.split(",") if o.strip()] if origins_str else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],   # POST / OPTIONS / GET и т.д.
    allow_headers=["*"],   # в т.ч. X-Telegram-InitData
)

# ---------------------------- Lifecycle ----------------------------

@app.on_event("startup")
def on_startup() -> None:
    init_db()

@app.get("/")
def root():
    return {"ok": True, "service": "transfer-api"}

@app.get("/health")
def health():
    return "ok"

# -------------------------- Валидации ------------------------------

def validate_capacity(vehicle_class: VehicleClass, pax: int) -> None:
    """
    Проверка вместимости по типу авто:
    - Минивэн: до 6 пассажиров
    - Остальные классы: до 3 пассажиров
    """
    cap = 6 if vehicle_class == VehicleClass.minivan else 3
    if pax > cap:
        raise HTTPException(
            status_code=422,
            detail=f"Для класса {vehicle_class.value} максимум {cap} пассажиров.",
        )

def validate_datetime(dt: datetime) -> None:
    """
    Дата/время не раньше чем через 30 минут от текущего момента.
    Сравнение выполняем в UTC, корректно обрабатывая часовой пояс входного значения.
    """
    # Нормализуем входную дату к UTC
    if dt.tzinfo is None:
        dt_utc = dt.replace(tzinfo=timezone.utc)
    else:
        dt_utc = dt.astimezone(timezone.utc)

    min_dt_utc = datetime.now(timezone.utc) + timedelta(minutes=30)
    if dt_utc < min_dt_utc:
        raise HTTPException(
            status_code=422,
            detail="Дата/время должны быть не раньше чем через 30 минут.",
        )

# --------------------------- Утилиты -------------------------------

VEHICLE_LABELS = {
    "standard": "Стандарт",
    "comfort":  "Комфорт",
    "business": "Бизнес",
    "premium":  "Премиум",
    "minivan":  "Минивэн",
}
CONTACT_LABELS = {
    "whatsapp": "WhatsApp",
    "telegram": "Telegram",
    "call":     "Звонок",
}

def human_vehicle_label(v: VehicleClass | str) -> str:
    value = v.value if hasattr(v, "value") else str(v)
    return VEHICLE_LABELS.get(value, value)

def human_contact_label(s: str) -> str:
    value = s.value if hasattr(s, "value") else str(s)
    return CONTACT_LABELS.get(value, value)

def human_datetime(dt: datetime) -> str:
    """
    Возвращает строку вида:
    06.10.2025 02:42 (UTC+05:00)
    Отображаем в том часовом поясе, в котором пришла дата; если tz нет — считаем UTC.
    """
    if dt.tzinfo is None:
        dt_local = dt.replace(tzinfo=timezone.utc)
    else:
        dt_local = dt

    offset = dt_local.utcoffset() or timedelta(0)
    total_min = int(offset.total_seconds() // 60)
    sign = "+" if total_min >= 0 else "-"
    hh = abs(total_min) // 60
    mm = abs(total_min) % 60
    offset_str = f"{sign}{hh:02d}:{mm:02d}"

    return f"{dt_local.strftime('%d.%m.%Y %H:%M')} (UTC{offset_str})"

def _digits_only(phone: str) -> str:
    """Оставляет только цифры (нужно для wa.me)."""
    return "".join(ch for ch in phone if ch.isdigit())

def build_contact_lines(phone: str, contact_method: str, transfer_id: str) -> list[str]:
    """
    Возвращает список строк для блока контакта:
    - всегда даём кликабельный телефон (tel:+7...)
    - если выбран WhatsApp — добавляем ссылку wa.me с предзаполненным текстом
    - для Telegram/Звонка оставляем явную пометку способа связи
    """
    label = human_contact_label(contact_method)
    tel_link = f"tel:{phone}"
    lines = [f"Контакт: <a href=\"{tel_link}\">{phone}</a> ({label})"]

    method_value = contact_method.value if hasattr(contact_method, "value") else str(contact_method)
    if method_value == "whatsapp":
        digits = _digits_only(phone)
        if digits:
            text = f"Здравствуйте! Интерес по заявке ID {transfer_id}"
            wa = f"https://wa.me/{digits}?text={quote(text)}"
            lines.append(f"Ссылка для WhatsApp: {wa}")

    return lines

def build_transfer_text(data: TransferCreate, transfer_id: str) -> str:
    """
    Формирует понятный текст уведомления о заявке без смайликов и сырых enum'ов.
    Добавляет кликабельный телефон и wa.me при выборе WhatsApp.
    """
    veh = human_vehicle_label(data.vehicle_class)
    contact_lines = build_contact_lines(data.contact_phone, data.contact_method, transfer_id)
    dt_str = human_datetime(data.datetime)

    luggage_str = "да" if data.luggage else "нет"
    childseat_str = "да" if data.child_seat else "нет"
    comment_block = f"\nКомментарий: {data.comment}" if (data.comment or "").strip() else ""

    base = (
        "Новая заявка на трансфер\n"
        f"Когда: {dt_str}\n"
        f"Класс автомобиля: {veh}\n"
        f"Пассажиров: {data.pax_count}\n"
        f"Багаж: {luggage_str}\n"
        f"Детское кресло: {childseat_str}\n"
        f"Откуда: {data.departure_city}, {data.departure_address}\n"
        f"Куда: {data.arrival_city}, {data.arrival_address}\n"
        + "\n".join(contact_lines) +
        f"{comment_block}\n"
        f"ID заявки: {transfer_id}"
    )
    return base

# ---------------------------- Endpoint -----------------------------

@app.post("/transfers", response_model=TransferRead, status_code=201)
async def create_transfer(
    data: TransferCreate,
    request: Request,
    session: Session = Depends(get_session),
    # Принимаем оба варианта заголовка (на фронте используем X-Telegram-InitData):
    x_init_1: str | None = Header(None, alias="X-Telegram-InitData"),
    x_init_2: str | None = Header(None, alias="X-Telegram-Init-Data"),
):
    """
    Создание новой заявки.
    Валидации:
      - Проверка initData (если включена через env),
      - Проверка вместимости по классу авто,
      - Проверка минимального времени выезда.
    """
    # 1) initData: берём из заголовков, затем из тела
    init_data = (x_init_1 or x_init_2 or data.telegram_init_data or "").strip()

    # 2) Опциональная проверка подписи Telegram initData.
    #    Пока тестируете на внешнем домене, можно отключить через env:
    #    SKIP_INITDATA_VERIFY=true
    if not settings.SKIP_INITDATA_VERIFY and settings.BOT_TOKEN:
        from .security import verify_telegram_init_data
        if not init_data or not verify_telegram_init_data(init_data):
            raise HTTPException(status_code=401, detail="Invalid Telegram init data")

    # 3) Бизнес-валидации
    validate_capacity(data.vehicle_class, data.pax_count)
    validate_datetime(data.datetime)

    # 4) Запись в БД
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

    # 5) Отправка уведомления в Telegram (если настроены FORWARD_* переменные)
    text = build_transfer_text(data, transfer.id)
    try:
        await forward_transfer_message(text)
    except Exception:
        # уведомление не критично для успеха запроса
        pass

    return TransferRead(id=transfer.id, status="accepted")
