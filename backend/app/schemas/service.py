from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.service import ServiceType


class ServiceBase(BaseModel):
    name: str
    description: Optional[str] = None
    service_type: ServiceType
    max_sessions: int
    max_participants: Optional[int] = None
    duration_minutes: int = 60


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    max_participants: Optional[int] = None
    duration_minutes: Optional[int] = None
    is_active: Optional[bool] = None


class ServiceResponse(ServiceBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True
