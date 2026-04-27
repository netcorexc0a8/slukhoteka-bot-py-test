from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.client_subscription import SubscriptionStatus
from app.models.service import ServiceType


class ClientSubscriptionCreate(BaseModel):
    """
    Выдача абонемента клиенту.

    Логика валидации (на стороне backend, не Pydantic):
    - Для индивидуальных абонементов assigned_specialist_id обязателен.
    - Для алгоритмики group_id обязателен.
    - total_sessions берётся из services.max_sessions, frontend его не задаёт.
    """
    client_id: int
    service_id: int
    assigned_specialist_id: Optional[int] = None
    group_id: Optional[str] = None
    valid_until: Optional[datetime] = None
    notes: Optional[str] = None


class ClientSubscriptionUpdate(BaseModel):
    status: Optional[SubscriptionStatus] = None
    valid_until: Optional[datetime] = None
    notes: Optional[str] = None
    assigned_specialist_id: Optional[int] = None


class ClientSubscriptionResponse(BaseModel):
    id: int
    client_id: int
    service_id: int
    assigned_specialist_id: Optional[int] = None
    group_id: Optional[str] = None
    total_sessions: int
    used_sessions: int
    # remaining_sessions подхватывается из @property на ORM-модели
    remaining_sessions: int
    status: SubscriptionStatus
    purchased_at: datetime
    valid_until: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    # Денормализованные удобные поля для UI (заполняются на уровне API endpoint)
    client_name: Optional[str] = None
    service_name: Optional[str] = None
    service_type: Optional[ServiceType] = None
    assigned_specialist_name: Optional[str] = None
    group_name: Optional[str] = None

    class Config:
        from_attributes = True
