from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.schemas.user import GlobalUserResponse, GlobalUserUpdate
from app.crud.user import get_all_users, update_user_role, delete_user, get_user_by_id
from app.schemas.invite import InviteCodeCreate, InviteCodeResponse
from app.crud.invite import create_invite_code, get_invite_code_by_code, use_invite_code
from app.models.user import Role, GlobalUser

router = APIRouter()

@router.get("", response_model=List[GlobalUserResponse])
def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    users = get_all_users(db, skip, limit)
    return users

@router.put("/{user_id}", response_model=GlobalUserResponse)
def update_user(
    user_id: int,
    user_update: GlobalUserUpdate,
    db: Session = Depends(get_db)
):
    user = update_user_role(db, user_id, user_update.role, user_update.name)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    return user

@router.get("/{user_id}", response_model=GlobalUserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_endpoint(user_id: int, db: Session = Depends(get_db)):
    success = delete_user(db, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    return None

@router.post("/invite", response_model=InviteCodeResponse, status_code=status.HTTP_201_CREATED)
def create_invite(
    invite: InviteCodeCreate,
    db: Session = Depends(get_db)
):
    return create_invite_code(db, invite)

@router.get("/invite/check")
def check_invite_code(
    code: str = Query(..., description="Код приглашения"),
    db: Session = Depends(get_db)
):
    """Проверяет валидность invite code"""
    from app.crud.invite import get_invite_code_by_code
    invite = get_invite_code_by_code(db, code)

    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Код не найден"
        )

    if invite.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Код уже использован"
        )

    return {"valid": True, "role": invite.role.value}

@router.post("/invite/use")
def use_invite_code_endpoint(
    code: str,
    user_id: int,
    db: Session = Depends(get_db)
):
    """Помечает invite code как использованный"""
    from app.crud.invite import use_invite_code

    result = use_invite_code(db, code, user_id)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный или уже использованный код"
        )

    return {"success": True}
