from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.schemas.client import ClientCreate, ClientUpdate, ClientResponse
from app.crud.client import (
    get_clients_by_user, get_client_by_id, get_client_by_phone,
    create_client, update_client, delete_client
)

router = APIRouter()

@router.get("", response_model=list[ClientResponse])
def get_clients(
    user_id: int = Query(..., description="ID пользователя"),
    include_deleted: bool = False,
    db: Session = Depends(get_db)
):
    clients = get_clients_by_user(db, user_id, include_deleted)
    return clients

@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client_endpoint(client: ClientCreate, db: Session = Depends(get_db)):
    existing_client = get_client_by_phone(db, client.phone, client.global_user_id)
    if existing_client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Клиент с таким номером телефона уже существует"
        )

    return create_client(db, client)

@router.get("/{client_id}", response_model=ClientResponse)
def get_client(client_id: int, db: Session = Depends(get_db)):
    client = get_client_by_id(db, client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клиент не найден"
        )
    return client

@router.put("/{client_id}", response_model=ClientResponse)
def update_client_endpoint(
    client_id: int,
    client_update: ClientUpdate,
    db: Session = Depends(get_db)
):
    client = update_client(db, client_id, client_update)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клиент не найден"
        )
    return client

@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client_endpoint(client_id: int, db: Session = Depends(get_db)):
    success = delete_client(db, client_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Клиент не найден"
        )
    return None
