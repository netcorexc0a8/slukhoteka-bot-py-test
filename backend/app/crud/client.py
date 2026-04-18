from sqlalchemy.orm import Session, joinedload
from datetime import datetime
from typing import Optional, List
from app.models.client import Client
from app.schemas.client import ClientCreate, ClientUpdate

def get_clients_by_user(db: Session, user_id: int, include_deleted: bool = False) -> List[Client]:
    query = db.query(Client).filter(Client.global_user_id == user_id)

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
