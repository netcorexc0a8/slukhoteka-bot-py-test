from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class GroupBase(BaseModel):
    name: str
    service_id: int
    max_participants: int = 8
    day_of_week: Optional[int] = None
    time: Optional[str] = None


class GroupCreate(GroupBase):
    pass


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    max_participants: Optional[int] = None
    day_of_week: Optional[int] = None
    time: Optional[str] = None
    is_active: Optional[bool] = None


class GroupParticipantInfo(BaseModel):
    id: int
    client_id: int
    client_name: str
    client_phone: str
    joined_at: datetime
    is_active: bool
    left_at: Optional[datetime] = None


class GroupResponse(GroupBase):
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    participants: List[GroupParticipantInfo] = []

    class Config:
        from_attributes = True
