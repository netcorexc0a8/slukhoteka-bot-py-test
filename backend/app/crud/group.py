"""CRUD для групп (только для алгоритмики)."""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session, joinedload

from app.models.group import Group, GroupParticipant
from app.models.service import Service
from app.schemas.group import GroupCreate, GroupUpdate
from app.services.exceptions import InvalidSubscriptionConfig


def get_group_by_id(db: Session, group_id: str) -> Optional[Group]:
    return (
        db.query(Group)
        .options(joinedload(Group.group_participants).joinedload(GroupParticipant.client))
        .filter(Group.id == group_id, Group.deleted_at.is_(None))
        .first()
    )


def get_active_groups(db: Session, service_id: Optional[int] = None) -> List[Group]:
    query = db.query(Group).filter(
        Group.is_active.is_(True), Group.deleted_at.is_(None)
    )
    if service_id is not None:
        query = query.filter(Group.service_id == service_id)
    return query.order_by(Group.name).all()


def create_group(db: Session, payload: GroupCreate) -> Group:
    service = db.query(Service).filter(Service.id == payload.service_id).first()
    if service is None or not service.is_group:
        raise InvalidSubscriptionConfig(
            "Группы можно создавать только для групповых услуг (алгоритмика)"
        )
    # Проверка на дубль по названию (без учёта регистра) среди активных групп
    existing = (
        db.query(Group)
        .filter(
            Group.deleted_at.is_(None),
            Group.is_active.is_(True),
            Group.service_id == payload.service_id,
        )
        .all()
    )
    name_lower = payload.name.strip().lower()
    for g in existing:
        if (g.name or "").strip().lower() == name_lower:
            raise InvalidSubscriptionConfig(
                f"Группа с названием «{payload.name}» уже существует"
            )
    group = Group(
        id=str(uuid.uuid4()),
        name=payload.name,
        service_id=payload.service_id,
        max_participants=payload.max_participants,
        day_of_week=payload.day_of_week,
        time=payload.time,
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


def update_group(db: Session, group_id: str, payload: GroupUpdate) -> Optional[Group]:
    group = get_group_by_id(db, group_id)
    if not group:
        return None
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(group, field, value)
    db.commit()
    db.refresh(group)
    return group


def delete_group(db: Session, group_id: str) -> bool:
    group = get_group_by_id(db, group_id)
    if not group:
        return False
    group.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return True


def add_participant(db: Session, group_id: str, client_id: int) -> Optional[GroupParticipant]:
    """Добавить клиента в группу. Если уже состоит — реактивируем."""
    existing = (
        db.query(GroupParticipant)
        .filter(
            GroupParticipant.group_id == group_id,
            GroupParticipant.client_id == client_id,
        )
        .first()
    )
    if existing:
        existing.is_active = True
        existing.left_at = None
        db.commit()
        db.refresh(existing)
        return existing

    participant = GroupParticipant(group_id=group_id, client_id=client_id)
    db.add(participant)
    db.commit()
    db.refresh(participant)
    return participant


def remove_participant(db: Session, group_id: str, client_id: int) -> bool:
    participant = (
        db.query(GroupParticipant)
        .filter(
            GroupParticipant.group_id == group_id,
            GroupParticipant.client_id == client_id,
            GroupParticipant.is_active.is_(True),
        )
        .first()
    )
    if not participant:
        return False
    participant.is_active = False
    participant.left_at = datetime.now(timezone.utc)
    db.commit()
    return True