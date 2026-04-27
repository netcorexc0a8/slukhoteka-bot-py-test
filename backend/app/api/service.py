from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.service import ServiceResponse
from app.crud.service import get_active_services

router = APIRouter()


@router.get("", response_model=list[ServiceResponse])
def list_services(db: Session = Depends(get_db)):
    """Справочник доступных услуг (типов абонементов)."""
    return get_active_services(db)
