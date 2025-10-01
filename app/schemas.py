from pydantic import BaseModel, Field, constr, conint
from datetime import datetime
from typing import Optional
import uuid
from .models import VehicleClass, ContactMethod

PhoneE164 = constr(pattern=r"^\+\d{10,15}$")

class TransferCreate(BaseModel):
    departure_city: str
    departure_address: str
    arrival_city: str
    arrival_address: str
    datetime: datetime
    vehicle_class: VehicleClass
    pax_count: conint(ge=1, le=20)
    luggage: bool = False
    child_seat: bool = False
    contact_phone: PhoneE164
    contact_method: ContactMethod
    comment: Optional[str] = Field(default=None, max_length=300)
    telegram_init_data: str

class TransferRead(BaseModel):
    id: uuid.UUID
    status: str = "accepted"
