# Собираем все модели здесь, чтобы Base.metadata знал о них при create_all/миграциях
from app.models.user import GlobalUser, PlatformUser, Role
from app.models.client import Client
from app.models.invite import InviteCode
from app.models.service import Service, ServiceType
from app.models.group import Group, GroupParticipant
from app.models.client_subscription import ClientSubscription, SubscriptionStatus
from app.models.booking import Booking, BookingStatus, BookingType, booking_specialists

# Старая модель Schedule удаляется миграцией 003 — больше не импортируем

__all__ = [
    "GlobalUser", "PlatformUser", "Role",
    "Client",
    "InviteCode",
    "Service", "ServiceType",
    "Group", "GroupParticipant",
    "ClientSubscription", "SubscriptionStatus",
    "Booking", "BookingStatus", "BookingType", "booking_specialists",
]
