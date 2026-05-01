from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ClientBase(BaseModel):
    name: str
    phone: Optional[str] = None


class ClientCreate(ClientBase):
    global_user_id: int


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    global_user_id: Optional[int] = None  # для передачи клиента другому специалисту


class ClientTransferRequest(BaseModel):
    """Передача клиента другому специалисту."""
    new_owner_id: int


class ClientResponse(ClientBase):
    id: int
    global_user_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True
