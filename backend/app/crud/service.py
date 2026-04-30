from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.service import Service, ServiceType


def get_active_services(db: Session) -> List[Service]:
    return (
        db.query(Service)
        .filter(Service.is_active.is_(True), Service.deleted_at.is_(None))
        .order_by(Service.id)
        .all()
    )


def get_service_by_id(db: Session, service_id: int) -> Optional[Service]:
    return db.query(Service).filter(Service.id == service_id).first()


def get_service_by_type(db: Session, service_type: ServiceType) -> Optional[Service]:
    return db.query(Service).filter(Service.service_type == service_type).first()
