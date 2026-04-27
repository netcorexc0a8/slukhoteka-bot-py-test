from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class ServiceType(str, enum.Enum):
    DIAGNOSTICS = "diagnostics"
    SUBSCRIPTION_1 = "subscription_1"
    SUBSCRIPTION_4 = "subscription_4"
    SUBSCRIPTION_8 = "subscription_8"
    LOGORHYTHMICS = "logorhythmics"


class Service(Base):
    """
    Справочник услуг (типов абонементов).
    Засеивается миграцией 003 пятью записями.
    """
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    # values_callable — маппим через .value (нижний регистр), а не через имена членов
    service_type = Column(
        SAEnum(
            ServiceType,
            name="service_type_enum",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        index=True,
        unique=True,
    )
    max_sessions = Column(Integer, nullable=False)
    max_participants = Column(Integer, nullable=True)
    duration_minutes = Column(Integer, default=60, nullable=False)
    is_group = Column(Boolean, default=False, nullable=False)
    weekly_limit = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)

    bookings = relationship("Booking", back_populates="service")
    groups = relationship("Group", back_populates="service")
    subscriptions = relationship("ClientSubscription", back_populates="service")