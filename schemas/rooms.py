from pydantic import BaseModel, Field
from typing import Optional


class RoomBase(BaseModel):
    room_number: str
    price: int
    status: Optional[str] = "available"


class RoomCreate(RoomBase):
    pass


class RoomUpdate(BaseModel):
    room_number: Optional[str]
    price: Optional[int]
    status: Optional[str]


class RoomOut(RoomBase):
    id: str = Field(..., alias="_id")
    current_contract: Optional[dict]

    class Config:
        allow_population_by_field_name = True
