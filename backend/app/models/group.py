from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Group(Base):
    """
    Группа для алгоритмики.

    Постоянных ведущих у группы НЕТ — состав ведущих фиксируется на уровне
    конкретного занятия (Booking + booking_specialists). Здесь только
    "паспорт" группы: название, расписание по умолчанию, макс. участников.
    """
    __tablename__ = "groups"

    id = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="RESTRICT"), nullable=False, index=True)
    max_participants = Column(Integer, nullable=False, default=8)
    # Дефолтное расписание группы (для подсказок при создании занятий)
    day_of_week = Column(Integer, nullable=True)  # 0..6 (Mon..Sun)
    time = Column(String(5), nullable=True)        # 'HH:MM'
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    service = relationship("Service", back_populates="groups")
    bookings = relationship("Booking", back_populates="group")
    group_participants = relationship(
        "GroupParticipant",
        back_populates="group",
        cascade="all, delete-orphan",
    )
    subscriptions = relationship("ClientSubscription", back_populates="group")


class GroupParticipant(Base):
    """Постоянные участники группы (клиенты)."""
    __tablename__ = "group_participants"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(String(100), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    joined_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    left_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    group = relationship("Group", back_populates="group_participants")
    client = relationship("Client")
