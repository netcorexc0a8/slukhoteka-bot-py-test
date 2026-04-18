from pydantic import BaseModel
from datetime import datetime
from app.models.user import Role

class GlobalUserBase(BaseModel):
    phone: str
    name: str | None = None
    role: Role

class GlobalUserCreate(GlobalUserBase):
    pass

class GlobalUserUpdate(BaseModel):
    name: str | None = None
    role: Role | None = None

class GlobalUserResponse(GlobalUserBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PlatformUserCreate(BaseModel):
    global_user_id: int
    platform: str
    external_id: str

class PlatformUserResponse(BaseModel):
    id: int
    global_user_id: int
    platform: str
    external_id: str
    created_at: datetime

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    phone: str
    platform: str
    external_id: str
    name: str | None = None
    role: Role | None = None

class LoginResponse(BaseModel):
    global_user_id: int
    role: Role
    platform_user_id: int
    name: str | None = None
