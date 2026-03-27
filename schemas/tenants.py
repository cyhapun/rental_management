from pydantic import BaseModel
from typing import Optional
from typing import List


class TenantBase(BaseModel):
    full_name: str
    cccd: str
    gender: Optional[str]
    birth_year: Optional[int]
    phone: Optional[str]


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    full_name: Optional[str]
    gender: Optional[str]
    birth_year: Optional[int]
    phone: Optional[str]


class TenantOut(TenantBase):
    id: str = ""
    contracts: Optional[List[dict]]

    class Config:
        orm_mode = True
