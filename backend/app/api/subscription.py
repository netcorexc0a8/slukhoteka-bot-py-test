from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app.schemas.client_subscription import (
    ClientSubscriptionCreate, ClientSubscriptionUpdate, ClientSubscriptionResponse,
)
from app.crud.subscription import (
    get_subscription_by_id, get_subscriptions_by_client,
    create_subscription, update_subscription, delete_subscription,
)
from app.services.exceptions import InvalidSubscriptionConfig

router = APIRouter()


def _to_response(sub) -> ClientSubscriptionResponse:
    """Конвертирует ORM-объект в Response с денормализованными полями."""
    return ClientSubscriptionResponse(
        id=sub.id,
        client_id=sub.client_id,
        service_id=sub.service_id,
        assigned_specialist_id=sub.assigned_specialist_id,
        group_id=sub.group_id,
        total_sessions=sub.total_sessions,
        used_sessions=sub.used_sessions,
        remaining_sessions=sub.remaining_sessions,
        status=sub.status,
        purchased_at=sub.purchased_at,
        valid_until=sub.valid_until,
        notes=sub.notes,
        created_at=sub.created_at,
        updated_at=sub.updated_at,
        deleted_at=sub.deleted_at,
        client_name=sub.client.name if sub.client else None,
        service_name=sub.service.name if sub.service else None,
        service_type=sub.service.service_type if sub.service else None,
        assigned_specialist_name=(
            sub.assigned_specialist.name if sub.assigned_specialist else None
        ),
        group_name=sub.group.name if sub.group else None,
    )


@router.get("", response_model=List[ClientSubscriptionResponse])
def list_subscriptions(
    client_id: int = Query(..., description="ID клиента"),
    only_active: bool = False,
    only_usable: bool = Query(False, description="Только активные с остатком сессий"),
    db: Session = Depends(get_db),
):
    """Список абонементов клиента."""
    subs = get_subscriptions_by_client(
        db, client_id, only_active=only_active, only_usable=only_usable
    )
    return [_to_response(s) for s in subs]


@router.post("", response_model=ClientSubscriptionResponse, status_code=status.HTTP_201_CREATED)
def create_subscription_endpoint(
    payload: ClientSubscriptionCreate,
    db: Session = Depends(get_db),
):
    """Выдать клиенту новый абонемент."""
    try:
        sub = create_subscription(db, payload)
    except InvalidSubscriptionConfig as e:
        raise HTTPException(status_code=400, detail=str(e))
    # Перезагружаем со связями для корректного response
    sub = get_subscription_by_id(db, sub.id)
    return _to_response(sub)


@router.get("/{subscription_id}", response_model=ClientSubscriptionResponse)
def get_subscription_endpoint(subscription_id: int, db: Session = Depends(get_db)):
    sub = get_subscription_by_id(db, subscription_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Абонемент не найден")
    return _to_response(sub)


@router.put("/{subscription_id}", response_model=ClientSubscriptionResponse)
def update_subscription_endpoint(
    subscription_id: int,
    payload: ClientSubscriptionUpdate,
    db: Session = Depends(get_db),
):
    sub = update_subscription(db, subscription_id, payload)
    if not sub:
        raise HTTPException(status_code=404, detail="Абонемент не найден")
    return _to_response(sub)


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription_endpoint(subscription_id: int, db: Session = Depends(get_db)):
    if not delete_subscription(db, subscription_id):
        raise HTTPException(status_code=404, detail="Абонемент не найден")
    return None
