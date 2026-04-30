from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.schemas.group import GroupCreate, GroupUpdate, GroupResponse, GroupParticipantInfo
from app.crud.group import (
    get_group_by_id, get_active_groups,
    create_group, update_group, delete_group,
    add_participant, remove_participant,
)
from app.services.exceptions import InvalidSubscriptionConfig

router = APIRouter()


def _to_response(group) -> GroupResponse:
    participants = [
        GroupParticipantInfo(
            id=p.id,
            client_id=p.client_id,
            client_name=p.client.name,
            client_phone=p.client.phone,
            joined_at=p.joined_at,
            is_active=p.is_active,
            left_at=p.left_at,
        )
        for p in group.group_participants
        if p.client is not None
    ]
    return GroupResponse(
        id=group.id,
        name=group.name,
        service_id=group.service_id,
        max_participants=group.max_participants,
        day_of_week=group.day_of_week,
        time=group.time,
        is_active=group.is_active,
        created_at=group.created_at,
        updated_at=group.updated_at,
        deleted_at=group.deleted_at,
        participants=participants,
    )


@router.get("", response_model=List[GroupResponse])
def list_groups(
    service_id: Optional[int] = Query(None, description="Фильтр по услуге"),
    db: Session = Depends(get_db),
):
    groups = get_active_groups(db, service_id=service_id)
    # Догружаем участников
    return [_to_response(get_group_by_id(db, g.id)) for g in groups]


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
def create_group_endpoint(payload: GroupCreate, db: Session = Depends(get_db)):
    try:
        group = create_group(db, payload)
    except InvalidSubscriptionConfig as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _to_response(get_group_by_id(db, group.id))


@router.get("/{group_id}", response_model=GroupResponse)
def get_group_endpoint(group_id: str, db: Session = Depends(get_db)):
    group = get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Группа не найдена")
    return _to_response(group)


@router.put("/{group_id}", response_model=GroupResponse)
def update_group_endpoint(group_id: str, payload: GroupUpdate, db: Session = Depends(get_db)):
    group = update_group(db, group_id, payload)
    if not group:
        raise HTTPException(status_code=404, detail="Группа не найдена")
    return _to_response(get_group_by_id(db, group.id))


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group_endpoint(group_id: str, db: Session = Depends(get_db)):
    if not delete_group(db, group_id):
        raise HTTPException(status_code=404, detail="Группа не найдена")
    return None


@router.post("/{group_id}/participants/{client_id}", status_code=status.HTTP_201_CREATED)
def add_participant_endpoint(group_id: str, client_id: int, db: Session = Depends(get_db)):
    group = get_group_by_id(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Группа не найдена")
    add_participant(db, group_id, client_id)
    return {"success": True}


@router.delete("/{group_id}/participants/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_participant_endpoint(group_id: str, client_id: int, db: Session = Depends(get_db)):
    if not remove_participant(db, group_id, client_id):
        raise HTTPException(status_code=404, detail="Участник не найден")
    return None
