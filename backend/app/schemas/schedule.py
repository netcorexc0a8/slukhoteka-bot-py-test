from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ScheduleBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    is_recurring: Optional[bool] = False

class ScheduleCreate(ScheduleBase):
    global_user_id: int
    recurrence_group_id: Optional[str] = None

class ScheduleUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    recurrence_group_id: Optional[str] = None

class ScheduleResponse(ScheduleBase):
    id: int
    global_user_id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    user_name: Optional[str] = None
    recurrence_group_id: Optional[str] = None

    class Config:
        from_attributes = True
