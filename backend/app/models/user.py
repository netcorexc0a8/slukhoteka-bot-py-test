from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class Role(str, enum.Enum):
    ADMIN = "admin"
    METHODIST = "methodist"
    SPECIALIST = "specialist"


class GlobalUser(Base):
    __tablename__ = "global_users"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    role = Column(Enum(Role), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    platform_users = relationship(
        "PlatformUser", back_populates="global_user", cascade="all, delete-orphan"
    )
    clients = relationship(
        "Client", back_populates="global_user", cascade="all, delete-orphan"
    )
    invite_codes_created = relationship(
        "InviteCode",
        foreign_keys="InviteCode.created_by",
        back_populates="creator",
    )
    invite_codes_used = relationship(
        "InviteCode",
        foreign_keys="InviteCode.used_by",
        back_populates="user",
    )

    # Брони, в которых этот пользователь — основной ведущий специалист.
    # Без cascade: на уровне БД у bookings.specialist_id стоит ON DELETE RESTRICT —
    # удалить пользователя с активными бронями нельзя.
    bookings_as_specialist = relationship(
        "Booking",
        foreign_keys="Booking.specialist_id",
        backref="_specialist_user",
        viewonly=True,
    )
    # Абонементы, в которых этот пользователь — закреплённый специалист
    # (для индивидуальных абонементов).
    assigned_subscriptions = relationship(
        "ClientSubscription",
        foreign_keys="ClientSubscription.assigned_specialist_id",
        viewonly=True,
    )


class PlatformUser(Base):
    __tablename__ = "platform_users"

    id = Column(Integer, primary_key=True, index=True)
    global_user_id = Column(
        Integer, ForeignKey("global_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform = Column(String(20), nullable=False)
    external_id = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    global_user = relationship("GlobalUser", back_populates="platform_users")