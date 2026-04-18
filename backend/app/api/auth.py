from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user import LoginRequest, LoginResponse
from app.crud.user import get_or_create_global_user, create_or_update_platform_user, get_platform_user
from app.crud.invite import use_invite_code
from app.schemas.invite import UseInviteRequest, UseInviteResponse
from app.models.user import Role, GlobalUser

router = APIRouter()

@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    global_user = get_or_create_global_user(db, request.phone, request.name, request.role)
    platform_user = create_or_update_platform_user(
        db, global_user.id, request.platform, request.external_id
    )
    return LoginResponse(
        global_user_id=global_user.id,
        role=global_user.role,
        platform_user_id=platform_user.id,
        name=global_user.name
    )

@router.get("/check-phone")
def check_phone(
    phone: str = Query(..., description="Номер телефона"),
    db: Session = Depends(get_db)
):
    """
    Проверяет существование пользователя по номеру телефона
    Возвращает 200 если пользователь существует, 404 если нет
    """
    from app.crud.user import get_user_by_phone
    from app.utils.phone_normalizer import normalize_phone

    normalized_phone = normalize_phone(phone)
    user = get_user_by_phone(db, normalized_phone)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )

    return {"exists": True, "role": user.role.value}

@router.get("/check-auth", response_model=LoginResponse)
def check_auth(
    platform: str = Query(..., description="Платформа (telegram, vk)"),
    external_id: str = Query(..., description="Внешний ID пользователя"),
    db: Session = Depends(get_db)
):
    """
    Проверяет авторизацию пользователя по platform и external_id
    Если пользователь существует - возвращает данные авторизации
    Если нет - возвращает 404
    """
    platform_user = get_platform_user(db, platform, external_id)

    if not platform_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден. Необходима авторизация по номеру телефона"
        )

    return LoginResponse(
        global_user_id=platform_user.global_user_id,
        role=platform_user.global_user.role,
        platform_user_id=platform_user.id,
        name=platform_user.global_user.name
    )

@router.post("/use-invite", response_model=UseInviteResponse)
def use_invite(request: UseInviteRequest, db: Session = Depends(get_db)):
    invite = use_invite_code(db, request.code, request.user_id)
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный или уже использованный код приглашения"
        )

    from app.crud.user import update_user_role
    user = update_user_role(db, request.user_id, invite.role)

    return UseInviteResponse(
        success=True,
        new_role=user.role,
        message=f"Роль успешно изменена на {user.role.value}"
    )
