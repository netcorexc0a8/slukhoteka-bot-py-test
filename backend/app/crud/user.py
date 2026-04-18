from sqlalchemy.orm import Session
from app.models.user import GlobalUser, PlatformUser, Role
from app.schemas.user import GlobalUserCreate, PlatformUserCreate
from app.utils.phone_normalizer import normalize_phone
from app.config import settings
from datetime import datetime

def get_user_by_phone(db: Session, phone: str) -> GlobalUser:
    normalized_phone = normalize_phone(phone)
    return db.query(GlobalUser).filter(GlobalUser.phone == normalized_phone).first()

def create_global_user(db: Session, user: GlobalUserCreate) -> GlobalUser:
    normalized_phone = normalize_phone(user.phone)
    db_user = GlobalUser(
        phone=normalized_phone,
        name=user.name,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_or_create_global_user(db: Session, phone: str, name: str | None = None, role: Role | None = None) -> GlobalUser:
    normalized_phone = normalize_phone(phone)
    user = get_user_by_phone(db, normalized_phone)
    if not user:
        # Если роль не указана, используем SPECIALIST по умолчанию
        if not role:
            role = Role.ADMIN if normalized_phone in settings.admin_phones else Role.SPECIALIST
        user = create_global_user(db, GlobalUserCreate(phone=normalized_phone, name=name, role=role))
    elif name and not user.name:
        # Если имя не заполнено, обновляем его
        user.name = name
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
    return user

def get_platform_user(db: Session, platform: str, external_id: str) -> PlatformUser:
    return db.query(PlatformUser).filter(
        PlatformUser.platform == platform,
        PlatformUser.external_id == external_id
    ).first()

def create_or_update_platform_user(db: Session, global_user_id: int, platform: str, external_id: str) -> PlatformUser:
    platform_user = get_platform_user(db, platform, external_id)
    if not platform_user:
        platform_user = PlatformUser(
            global_user_id=global_user_id,
            platform=platform,
            external_id=external_id
        )
        db.add(platform_user)
        db.commit()
        db.refresh(platform_user)
    return platform_user

def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> list[GlobalUser]:
    return db.query(GlobalUser).offset(skip).limit(limit).all()

def get_user_by_id(db: Session, user_id: int) -> GlobalUser:
    return db.query(GlobalUser).filter(GlobalUser.id == user_id).first()

def update_user_role(db: Session, user_id: int, new_role: Role | None = None, new_name: str | None = None) -> GlobalUser:
    user = db.query(GlobalUser).filter(GlobalUser.id == user_id).first()
    if user:
        if new_role:
            user.role = new_role
        if new_name:
            user.name = new_name
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
    return user

def delete_user(db: Session, user_id: int) -> bool:
    user = db.query(GlobalUser).filter(GlobalUser.id == user_id).first()
    if user:
        db.delete(user)
        db.commit()
        return True
    return False
