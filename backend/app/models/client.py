from sqlalchemy import Column, Integer, String, DateTime, Boolean, Date, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False, index=True, unique=True)
    birth_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    bookings = relationship("Booking", back_populates="client", cascade="all, delete-orphan")
    group_participations = relationship("GroupParticipant", back_populates="client", cascade="all, delete-orphan")
