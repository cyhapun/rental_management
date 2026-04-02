from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class PaymentRecord(BaseModel):
    amount: int
    method: str
    date: datetime
    recorded_at: datetime


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
    
    paid_amount: int = 0
    paid_method: Optional[str] = None
    paid_at: Optional[datetime] = None
    payment_history: Optional[List[PaymentRecord]] = []