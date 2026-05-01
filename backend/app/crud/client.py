from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List, Tuple

from app.models.client import Client
from app.models.client_subscription import ClientSubscription, SubscriptionStatus
from app.models.user import GlobalUser
from app.models.booking import Booking
from app.schemas.client import ClientCreate, ClientUpdate


def get_clients_by_user(db: Session, user_id: int, include_deleted: bool = False) -> List[Client]:
    query = db.query(Client).filter(Client.global_user_id == user_id)
    if not include_deleted:
        query = query.filter(Client.deleted_at.is_(None))
    return query.order_by(Client.name).all()


def get_all_clients(db: Session, include_deleted: bool = False) -> List[Client]:
    """Все клиенты в системе. Используется для роли admin/methodist."""
    query = db.query(Client)
    if not include_deleted:
        query = query.filter(Client.deleted_at.is_(None))
    return query.order_by(Client.name).all()


def get_client_by_id(db: Session, client_id: int, include_deleted: bool = False) -> Optional[Client]:
    query = db.query(Client).filter(Client.id == client_id)
    if not include_deleted:
        query = query.filter(Client.deleted_at.is_(None))
    return query.first()


def get_client_by_phone(db: Session, phone: str, user_id: int, include_deleted: bool = False) -> Optional[Client]:
    query = db.query(Client).filter(Client.phone == phone, Client.global_user_id == user_id)
    if not include_deleted:
        query = query.filter(Client.deleted_at.is_(None))
    return query.first()


def create_client(db: Session, client: ClientCreate) -> Client:
    db_client = Client(**client.dict())
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client


def update_client(db: Session, client_id: int, client_update: ClientUpdate) -> Optional[Client]:
    db_client = get_client_by_id(db, client_id)
    if db_client:
        update_data = client_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_client, field, value)
        db_client.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_client)
    return db_client


def delete_client(db: Session, client_id: int) -> bool:
    db_client = get_client_by_id(db, client_id)
    if db_client:
        db_client.deleted_at = datetime.utcnow()
        db.commit()
        return True
    return False


def can_transfer_client(db: Session, client_id: int) -> Tuple[bool, str]:
    """
    Проверяет, можно ли передать клиента другому специалисту.

    Передача разрешена, если у клиента нет «не до конца использованных»
    активных абонементов. Условие: НЕТ абонемента где
    status=active И used_sessions < total_sessions.

    - Активный, но used == total — это «недозакрытый» абонемент, можно передавать.
    - Без абонементов вовсе — можно передавать.
    """
    blocking = (
        db.query(ClientSubscription)
        .filter(
            ClientSubscription.client_id == client_id,
            ClientSubscription.deleted_at.is_(None),
            ClientSubscription.status == SubscriptionStatus.ACTIVE,
            ClientSubscription.used_sessions < ClientSubscription.total_sessions,
        )
        .first()
    )
    if blocking is None:
        return True, ""

    service_name = blocking.service.name if blocking.service else "абонемент"
    remaining = blocking.total_sessions - blocking.used_sessions
    return False, (
        f"У клиента есть активный абонемент «{service_name}» "
        f"(осталось {remaining} занятий из {blocking.total_sessions}). "
        f"Передача возможна только когда все абонементы исчерпаны или отменены."
    )


def transfer_client(db: Session, client_id: int, new_owner_id: int) -> Tuple[Optional[Client], str]:
    """
    Меняет global_user_id клиента. Не трогает абонементы и брони —
    у них своя привязка через assigned_specialist_id.

    Возвращает (client, error_message). Если успех — error_message пустой.
    """
    client = get_client_by_id(db, client_id)
    if not client:
        return None, "Клиент не найден"

    new_owner = (
        db.query(GlobalUser)
        .filter(GlobalUser.id == new_owner_id)
        .first()
    )
    if not new_owner:
        return None, "Новый владелец не найден"

    if client.global_user_id == new_owner_id:
        return client, ""  # уже его, не трогаем

    can, reason = can_transfer_client(db, client_id)
    if not can:
        return None, reason

    client.global_user_id = new_owner_id
    client.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(client)
    return client, ""
