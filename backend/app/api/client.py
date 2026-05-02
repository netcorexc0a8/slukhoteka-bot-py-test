from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.schemas.client import (
    ClientCreate, ClientUpdate, ClientResponse, ClientTransferRequest,
)
from app.crud.client import (
    get_clients_by_user, get_all_clients,
    get_client_by_id, get_client_by_phone,
    create_client, update_client, delete_client,
    transfer_client, can_transfer_client,
)

router = APIRouter()


@router.get("", response_model=list[ClientResponse])
def get_clients(
    user_id: Optional[int] = Query(
        None,
        description="ID специалиста-владельца. Если не указан — возвращаются все клиенты (для admin/methodist).",
    ),
    include_deleted: bool = False,
    db: Session = Depends(get_db),
):
    if user_id is None:
        return get_all_clients(db, include_deleted)
    return get_clients_by_user(db, user_id, include_deleted)


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client_endpoint(client: ClientCreate, db: Session = Depends(get_db)):
    if client.phone and not client.phone.startswith("manual:"):
        # Дубль по телефону в рамках специалиста
        existing_client = get_client_by_phone(db, client.phone, client.global_user_id)
        if existing_client:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Клиент с таким номером телефона уже существует",
            )
    else:
        # Нет телефона — проверяем дубль по имени (без учёта регистра)
        from app.models.client import Client
        name_lower = (client.name or "").strip().lower()
        if name_lower:
            existing_by_name = (
                db.query(Client)
                .filter(
                    Client.global_user_id == client.global_user_id,
                    Client.deleted_at.is_(None),
                )
                .all()
            )
            for c in existing_by_name:
                if (c.name or "").strip().lower() == name_lower:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Клиент с именем «{client.name}» уже существует",
                    )
    return create_client(db, client)


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: int, db: Session = Depends(get_db)):
    client = get_client_by_id(db, client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клиент не найден",
        )
    return client


@router.put("/{client_id}", response_model=ClientResponse)
def update_client_endpoint(
    client_id: int,
    client_update: ClientUpdate,
    db: Session = Depends(get_db),
):
    client = update_client(db, client_id, client_update)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клиент не найден",
        )
    return client


@router.post("/{client_id}/transfer", response_model=ClientResponse)
def transfer_client_endpoint(
    client_id: int,
    payload: ClientTransferRequest,
    db: Session = Depends(get_db),
):
    """
    Передача клиента другому специалисту.

    Разрешено, только если у клиента нет недоиспользованных активных абонементов
    (status=active с used_sessions < total_sessions).
    """
    client, error = transfer_client(db, client_id, payload.new_owner_id)
    if error:
        if "не найден" in error:
            raise HTTPException(status_code=404, detail=error)
        raise HTTPException(status_code=409, detail=error)
    return client


@router.get("/{client_id}/can-transfer")
def can_transfer_client_endpoint(client_id: int, db: Session = Depends(get_db)):
    """Проверяет возможность передачи клиента (без её совершения)."""
    if not get_client_by_id(db, client_id):
        raise HTTPException(status_code=404, detail="Клиент не найден")
    can, reason = can_transfer_client(db, client_id)
    return {"can_transfer": can, "reason": reason}


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client_endpoint(client_id: int, db: Session = Depends(get_db)):
    success = delete_client(db, client_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клиент не найден",
        )
    return None