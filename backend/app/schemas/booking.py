from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.booking import BookingStatus, BookingType


class BookingBase(BaseModel):
    client_id: int
    service_id: int
    specialist_id: int
    start_time: datetime
    end_time: datetime
    booking_type: BookingType
    notes: Optional[str] = None


class BookingCreate(BookingBase):
    group_id: Optional[str] = None
    is_recurring: bool = False
    recurrence_group_id: Optional[str] = None
    session_number: Optional[int] = None


class BookingUpdate(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    notes: Optional[str] = None
    status: Optional[BookingStatus] = None


class BookingResponse(BookingBase):
    id: int
    group_id: Optional[str] = None
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

    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    specialist_name: Optional[str] = None
    service_name: Optional[str] = None
    group_name: Optional[str] = None

    class Config:
        from_attributes = True
