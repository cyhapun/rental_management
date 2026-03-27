from pydantic import BaseModel
from typing import Optional
from datetime import date


class ElectricReadingCreate(BaseModel):
    room_id: str
    month: str  # YYYY-MM
    old_index: Optional[int] = 0
    new_index: int
    usage: Optional[int]
    price_per_kwh: Optional[float] = 2000.0


class ElectricReadingOut(ElectricReadingCreate):
    id: str = ""
    room: Optional[dict]
    tenant: Optional[dict]
