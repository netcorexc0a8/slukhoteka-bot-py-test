from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.service import ServiceType


class ServiceResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    service_type: ServiceType
    max_sessions: int
    max_participants: Optional[int] = None
    duration_minutes: int
    is_group: bool
    weekly_limit: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
