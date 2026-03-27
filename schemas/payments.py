from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PaymentCreate(BaseModel):
    bill_id: str
    amount: int
    payment_date: Optional[datetime]
    method: Optional[str] = "cash"


class PaymentOut(PaymentCreate):
    id: str = ""
