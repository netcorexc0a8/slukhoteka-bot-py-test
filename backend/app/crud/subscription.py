"""CRUD для абонементов клиентов."""
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import Session, joinedload

from app.models.client_subscription import ClientSubscription, SubscriptionStatus
from app.models.service import Service
from app.models.client import Client
from app.models.booking import Booking, BookingStatus
from app.schemas.client_subscription import ClientSubscriptionCreate, ClientSubscriptionUpdate
from app.services.exceptions import InvalidSubscriptionConfig


def get_subscription_by_id(db: Session, subscription_id: int) -> Optional[ClientSubscription]:
    return (
        db.query(ClientSubscription)
        .options(
            joinedload(ClientSubscription.client),
            joinedload(ClientSubscription.service),
            joinedload(ClientSubscription.assigned_specialist),
            joinedload(ClientSubscription.group),
        )
        .filter(ClientSubscription.id == subscription_id, ClientSubscription.deleted_at.is_(None))
        .first()
    )


def get_subscriptions_by_client(
    db: Session,
    client_id: int,
    only_active: bool = False,
    only_usable: bool = False,
) -> List[ClientSubscription]:
    query = (
        db.query(ClientSubscription)
        .options(
            joinedload(ClientSubscription.service),
            joinedload(ClientSubscription.assigned_specialist),
            joinedload(ClientSubscription.group),
        )
        .filter(
            ClientSubscription.client_id == client_id,
            ClientSubscription.deleted_at.is_(None),
        )
    )
    if only_active or only_usable:
        query = query.filter(ClientSubscription.status == SubscriptionStatus.ACTIVE)
    if only_usable:
        query = query.filter(
            ClientSubscription.used_sessions < ClientSubscription.total_sessions
        )
    return query.order_by(ClientSubscription.purchased_at.desc()).all()


def create_subscription(db: Session, payload: ClientSubscriptionCreate) -> ClientSubscription:
    service = db.query(Service).filter(Service.id == payload.service_id).first()
    if service is None:
        raise InvalidSubscriptionConfig("Услуга не найдена")
    client = db.query(Client).filter(
        Client.id == payload.client_id, Client.deleted_at.is_(None)
    ).first()
    if client is None:
        raise InvalidSubscriptionConfig("Клиент не найден")

    if service.is_group:
        if not payload.group_id:
            raise InvalidSubscriptionConfig(
                "Для группового абонемента нужно указать group_id"
            )
        assigned_specialist_id = None
    else:
        if not payload.assigned_specialist_id:
            raise InvalidSubscriptionConfig(
                "Для индивидуального абонемента нужно указать assigned_specialist_id"
            )
        assigned_specialist_id = payload.assigned_specialist_id

    sub = ClientSubscription(
        client_id=payload.client_id,
        service_id=payload.service_id,
        assigned_specialist_id=assigned_specialist_id,
        group_id=payload.group_id if service.is_group else None,
        total_sessions=service.max_sessions,
        used_sessions=0,
        status=SubscriptionStatus.ACTIVE,
        valid_until=payload.valid_until,
        notes=payload.notes,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def _cancel_future_bookings(db: Session, subscription: ClientSubscription) -> int:
    """
    Отменяет (status=CANCELLED) все будущие активные брони абонемента.
    Сессии в счётчик не возвращаются — абонемент сам отменён.
    """
    now = datetime.now(timezone.utc)
    future = (
        db.query(Booking)
        .filter(
            Booking.subscription_id == subscription.id,
            Booking.deleted_at.is_(None),
            Booking.status == BookingStatus.SCHEDULED,
            Booking.start_time > now,
        )
        .all()
    )
    for b in future:
        b.status = BookingStatus.CANCELLED
        b.cancelled_at = now
    return len(future)


def update_subscription(
    db: Session, subscription_id: int, payload: ClientSubscriptionUpdate
) -> Optional[ClientSubscription]:
    sub = get_subscription_by_id(db, subscription_id)
    if not sub:
        return None
    data = payload.model_dump(exclude_unset=True)

    new_status = data.get("status")
    becoming_cancelled = (
        new_status == SubscriptionStatus.CANCELLED
        and sub.status != SubscriptionStatus.CANCELLED
    )

    for field, value in data.items():
        setattr(sub, field, value)

    if becoming_cancelled:
        _cancel_future_bookings(db, sub)

    db.commit()
    db.refresh(sub)
    return sub


def delete_subscription(db: Session, subscription_id: int) -> bool:
    sub = get_subscription_by_id(db, subscription_id)
    if not sub:
        return False
    sub.deleted_at = datetime.now(timezone.utc)
    sub.status = SubscriptionStatus.CANCELLED
    _cancel_future_bookings(db, sub)
    db.commit()
    return True