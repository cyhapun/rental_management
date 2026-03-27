from pydantic import BaseModel
from typing import Optional
from datetime import date


class ContractCreate(BaseModel):
    tenant_id: str
    room_id: str
    start_date: date
    end_date: Optional[date]
    contract_type: Optional[str]
    deposit: Optional[int] = 0


class ContractOut(ContractCreate):
    id: str = ""
    tenant: Optional[dict]
    room: Optional[dict]
