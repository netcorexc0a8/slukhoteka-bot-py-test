from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional


class ClientBase(BaseModel):
    name: str
    phone: str
    birth_date: Optional[date] = None
    notes: Optional[str] = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[date] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class ClientResponse(ClientBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True
