"""CRUD для абонементов клиентов."""
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import Session, joinedload

from app.models.client_subscription import ClientSubscription, SubscriptionStatus
from app.models.service import Service, ServiceType
from app.models.client import Client
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
    """
    only_active: статус ACTIVE.
    only_usable: ACTIVE + есть оставшиеся сессии (для UI выбора абонемента при бронировании).
    """
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
    """Выдача абонемента клиенту."""
    service = db.query(Service).filter(Service.id == payload.service_id).first()
    if service is None:
        raise InvalidSubscriptionConfig("Услуга не найдена")
    client = db.query(Client).filter(
        Client.id == payload.client_id, Client.deleted_at.is_(None)
    ).first()
    if client is None:
        raise InvalidSubscriptionConfig("Клиент не найден")

    # Валидация по типу услуги
    if service.is_group:
        if not payload.group_id:
            raise InvalidSubscriptionConfig(
                "Для группового абонемента (алгоритмика) нужно указать group_id"
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


def update_subscription(
    db: Session, subscription_id: int, payload: ClientSubscriptionUpdate
) -> Optional[ClientSubscription]:
    sub = get_subscription_by_id(db, subscription_id)
    if not sub:
        return None
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(sub, field, value)
    db.commit()
    db.refresh(sub)
    return sub


def delete_subscription(db: Session, subscription_id: int) -> bool:
    """Soft-delete. Записи (bookings) при этом продолжают существовать (FK SET NULL)."""
    sub = get_subscription_by_id(db, subscription_id)
    if not sub:
        return False
    sub.deleted_at = datetime.now(timezone.utc)
    sub.status = SubscriptionStatus.CANCELLED
    db.commit()
    return True
