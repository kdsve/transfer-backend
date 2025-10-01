from sqlmodel import SQLModel, Field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid

class VehicleClass(str, Enum):
    standard = "standard"
    comfort = "comfort"
    business = "business"
    minivan = "minivan"

class ContactMethod(str, Enum):
    whatsapp = "whatsapp"
    telegram = "telegram"
    call = "call"

class Transfer(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    departure_city: str
    departure_address: str
    arrival_city: str
    arrival_address: str
    datetime: datetime

    vehicle_class: VehicleClass
    pax_count: int
    luggage: bool = False
    child_seat: bool = False

    contact_phone: str
    contact_method: ContactMethod
    comment: Optional[str] = None

    telegram_init_data: str = ""
