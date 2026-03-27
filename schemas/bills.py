from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class BillCreate(BaseModel):
    contract_id: str
    month: str
    room_price: int
    electric_cost: int
    water_cost: int = 0
    other_cost: int = 0
    total: int
    status: str = "unpaid"


class BillOut(BillCreate):
    id: str = ""
    created_at: Optional[datetime]
