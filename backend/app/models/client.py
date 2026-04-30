from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    global_user_id = Column(Integer, ForeignKey("global_users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    global_user = relationship("GlobalUser", back_populates="clients")
    subscriptions = relationship(
        "ClientSubscription",
        back_populates="client",
        cascade="all, delete-orphan",
    )
    bookings = relationship(
        "Booking",
        back_populates="client",
        cascade="all, delete-orphan",
    )
