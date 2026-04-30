from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from app.models.booking import BookingStatus, BookingType


class BookingCreate(BaseModel):
    """
    Создание записи на занятие.

    Логика на backend:
    - subscription_id обязателен (бронь привязывается к абонементу клиента).
    - service_id, client_id, booking_type подтягиваются из подписки автоматически
      (но Pydantic их валидирует если переданы — для совместимости).
    - specialist_id для individual = subscription.assigned_specialist_id (если не передан).
    - co_specialist_ids — для group, основной + остальные ведущие.
    - Применяется валидация "не чаще 1 раза в неделю" (если service.weekly_limit).
    - Создание записи декрементит subscription.used_sessions += 1.
    """
    subscription_id: int
    start_time: datetime
    end_time: datetime
    specialist_id: Optional[int] = None  # обязателен для group; для individual возьмётся из подписки
    co_specialist_ids: Optional[List[int]] = None  # только для group; specialist_id в этот список не дублируется
    notes: Optional[str] = None


class BookingUpdate(BaseModel):
    """Обновление записи. Меняет время и/или статус, может добавить/убрать ведущих."""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    specialist_id: Optional[int] = None
    co_specialist_ids: Optional[List[int]] = None
    notes: Optional[str] = None
    status: Optional[BookingStatus] = None


class BookingResponse(BaseModel):
    id: int
    client_id: int
    subscription_id: Optional[int] = None
    service_id: int
    specialist_id: int
    group_id: Optional[str] = None

    start_time: datetime
    end_time: datetime

    booking_type: BookingType
    status: BookingStatus

    notes: Optional[str] = None
    is_recurring: bool
    recurrence_group_id: Optional[str] = None
    session_number: Optional[int] = None

    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancelled_by: Optional[int] = None

    # Денормализованные поля для UI
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    specialist_name: Optional[str] = None
    service_name: Optional[str] = None
    group_name: Optional[str] = None
    co_specialist_ids: List[int] = []
    co_specialist_names: List[str] = []

    # Прогресс по абонементу: "3/8"
    subscription_total: Optional[int] = None
    subscription_used: Optional[int] = None
    subscription_remaining: Optional[int] = None

    class Config:
        from_attributes = True
