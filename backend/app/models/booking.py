from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class BookingStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    MISSED = "missed"
    SPECIALIST_CANCELLED = "specialist_cancelled"


class BookingType(str, enum.Enum):
    INDIVIDUAL = "individual"
    GROUP = "group"


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="RESTRICT"), nullable=False, index=True)
    specialist_id = Column(Integer, ForeignKey("global_users.id", ondelete="RESTRICT"), nullable=False, index=True)
    group_id = Column(String(100), ForeignKey("groups.id", ondelete="SET NULL"), nullable=True, index=True)

    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False)

    booking_type = Column(Enum(BookingType), nullable=False, index=True)
    status = Column(Enum(BookingStatus), nullable=False, index=True, default=BookingStatus.SCHEDULED)

    notes = Column(Text, nullable=True)
    is_recurring = Column(Boolean, default=False, nullable=False)
    recurrence_group_id = Column(String(100), nullable=True, index=True)
    session_number = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_by = Column(Integer, ForeignKey("global_users.id", ondelete="SET NULL"), nullable=True)

    client = relationship("Client", back_populates="bookings")
    service = relationship("Service", back_populates="bookings")
    specialist = relationship("GlobalUser", foreign_keys=[specialist_id])
    group = relationship("Group", back_populates="bookings")
    cancelled_by_user = relationship("GlobalUser", foreign_keys=[cancelled_by])
