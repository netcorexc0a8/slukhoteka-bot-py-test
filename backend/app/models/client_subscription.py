from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey,
    CheckConstraint, Enum as SAEnum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ClientSubscription(Base):
    __tablename__ = "client_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="RESTRICT"), nullable=False, index=True)

    assigned_specialist_id = Column(
        Integer,
        ForeignKey("global_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    group_id = Column(
        String(100),
        ForeignKey("groups.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    total_sessions = Column(Integer, nullable=False)
    used_sessions = Column(Integer, nullable=False, default=0)

    status = Column(
        SAEnum(
            SubscriptionStatus,
            name="subscription_status_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=SubscriptionStatus.ACTIVE,
        index=True,
    )

    purchased_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    valid_until = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    __table_args__ = (
        CheckConstraint(
            "used_sessions >= 0 AND used_sessions <= total_sessions",
            name="chk_used_le_total",
        ),
    )

    client = relationship("Client", back_populates="subscriptions")
    service = relationship("Service", back_populates="subscriptions")
    assigned_specialist = relationship("GlobalUser", foreign_keys=[assigned_specialist_id])
    group = relationship("Group", back_populates="subscriptions")
    bookings = relationship("Booking", back_populates="subscription")

    @property
    def remaining_sessions(self) -> int:
        return max(0, self.total_sessions - self.used_sessions)

    @property
    def is_usable(self) -> bool:
        return (
            self.status == SubscriptionStatus.ACTIVE
            and self.deleted_at is None
            and self.remaining_sessions > 0
        )