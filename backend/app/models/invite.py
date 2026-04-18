from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from app.models.user import Role

class InviteCode(Base):
    __tablename__ = "invite_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(32), unique=True, nullable=False, index=True)
    role = Column(Enum(Role), nullable=False)
    used = Column(Boolean, default=False, index=True)
    created_by = Column(Integer, ForeignKey("global_users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    used_at = Column(DateTime(timezone=True), nullable=True)
    used_by = Column(Integer, ForeignKey("global_users.id"), nullable=True)

    creator = relationship("GlobalUser", foreign_keys=[created_by], back_populates="invite_codes_created")
    user = relationship("GlobalUser", foreign_keys=[used_by], back_populates="invite_codes_used")
