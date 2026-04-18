from pydantic import BaseModel
from datetime import datetime
from app.models.user import Role
from typing import Optional

class InviteCodeCreate(BaseModel):
    role: Role
    created_by: int

class InviteCodeResponse(BaseModel):
    id: int
    code: str
    role: Role
    used: bool
    created_at: datetime
    used_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UseInviteRequest(BaseModel):
    code: str
    user_id: int

class UseInviteResponse(BaseModel):
    success: bool
    new_role: Role
    message: str
