from sqlalchemy.orm import Session
from datetime import datetime
import secrets
from typing import Optional
from app.models.invite import InviteCode
from app.schemas.invite import InviteCodeCreate

def generate_invite_code() -> str:
    return secrets.token_urlsafe(16)

def create_invite_code(db: Session, invite: InviteCodeCreate) -> InviteCode:
    code = generate_invite_code()
    db_invite = InviteCode(
        code=code,
        role=invite.role,
        created_by=invite.created_by
    )
    db.add(db_invite)
    db.commit()
    db.refresh(db_invite)
    return db_invite

def get_invite_code_by_code(db: Session, code: str) -> Optional[InviteCode]:
    return db.query(InviteCode).filter(InviteCode.code == code).first()

def use_invite_code(db: Session, code: str, user_id: int) -> Optional[InviteCode]:
    invite = get_invite_code_by_code(db, code)
    if invite and not invite.used:
        invite.used = True
        invite.used_at = datetime.utcnow()
        invite.used_by = user_id
        db.commit()
        db.refresh(invite)
        return invite
    return None

def get_unused_invite_codes(db: Session, skip: int = 0, limit: int = 100) -> list[InviteCode]:
    return db.query(InviteCode).filter(InviteCode.used == False).offset(skip).limit(limit).all()
