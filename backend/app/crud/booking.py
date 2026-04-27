"""
CRUD для броней (Booking).

Ключевая логика:
- Создание брони обязательно привязано к ClientSubscription.
- Если подписка с weekly_limit (subscription_4 / subscription_8 / logorhythmics)
  и у клиента уже есть бронь в той же ISO-неделе — отказ.
- Создание брони инкрементит used_sessions подписки.
  Если used_sessions == total_sessions, подписка переводится в COMPLETED.
- Отмена/удаление брони (CANCELLED, SPECIALIST_CANCELLED) декрементит used_sessions
  и возвращает подписку в ACTIVE (если она была COMPLETED).
- MISSED не возвращает сессию (сгорает) — стандартное поведение.
"""
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from app.models.booking import Booking, BookingStatus, BookingType, booking_specialists
from app.models.client_subscription import ClientSubscription, SubscriptionStatus
from app.models.service import Service
from app.models.user import GlobalUser
from app.schemas.booking import BookingCreate, BookingUpdate
from app.services.exceptions import (
    SubscriptionNotFound, SubscriptionNotActive, SubscriptionExhausted,
    WeeklyLimitExceeded, TimeSlotConflict, InvalidSubscriptionConfig,
)
from app.utils.week import iso_week_bounds


# ---------- helpers ----------

def _has_specialist_conflict(
    db: Session,
    specialist_id: int,
    start_time: datetime,
    end_time: datetime,
    exclude_booking_id: Optional[int] = None,
) -> bool:
    """Проверяет, есть ли у специалиста другая бронь, пересекающаяся по времени."""
    query = db.query(Booking).filter(
        Booking.specialist_id == specialist_id,
        Booking.deleted_at.is_(None),
        Booking.status.notin_([BookingStatus.CANCELLED, BookingStatus.SPECIALIST_CANCELLED]),
        # Пересечение интервалов: existing.start < new.end AND existing.end > new.start
        Booking.start_time < end_time,
        Booking.end_time > start_time,
    )
    if exclude_booking_id is not None:
        query = query.filter(Booking.id != exclude_booking_id)
    return db.query(query.exists()).scalar()


def _check_weekly_limit(
    db: Session,
    subscription: ClientSubscription,
    start_time: datetime,
    exclude_booking_id: Optional[int] = None,
) -> None:
    """
    Если у service есть weekly_limit — проверяет, что у клиента нет другой
    активной брони по этой же подписке в той же ISO-неделе.
    """
    service = subscription.service
    if not service.weekly_limit:
        return

    week_start, week_end = iso_week_bounds(start_time)

    query = db.query(Booking).filter(
        Booking.subscription_id == subscription.id,
        Booking.deleted_at.is_(None),
        Booking.status.notin_([BookingStatus.CANCELLED, BookingStatus.SPECIALIST_CANCELLED]),
        Booking.start_time >= week_start,
        Booking.start_time < week_end,
    )
    if exclude_booking_id is not None:
        query = query.filter(Booking.id != exclude_booking_id)

    existing = query.order_by(Booking.start_time).first()
    if existing is not None:
        raise WeeklyLimitExceeded(existing_booking_time=existing.start_time)


def _bump_used_sessions(db: Session, subscription: ClientSubscription, delta: int) -> None:
    """Изменяет used_sessions на delta и обновляет статус подписки."""
    new_used = subscription.used_sessions + delta
    if new_used < 0:
        new_used = 0
    if new_used > subscription.total_sessions:
        new_used = subscription.total_sessions
    subscription.used_sessions = new_used

    if new_used >= subscription.total_sessions:
        subscription.status = SubscriptionStatus.COMPLETED
    elif subscription.status == SubscriptionStatus.COMPLETED and new_used < subscription.total_sessions:
        # Если отменили бронь у завершённой подписки — снова активна
        subscription.status = SubscriptionStatus.ACTIVE


def _set_co_specialists(db: Session, booking: Booking, specialist_ids: List[int]) -> None:
    """Перезаписывает m2m booking_specialists. Основной specialist_id включаем тоже."""
    # Удаляем текущие связи
    db.execute(
        booking_specialists.delete().where(booking_specialists.c.booking_id == booking.id)
    )
    # Гарантированно добавляем основного ведущего
    ids = set(specialist_ids or [])
    ids.add(booking.specialist_id)
    for sid in ids:
        db.execute(
            booking_specialists.insert().values(booking_id=booking.id, specialist_id=sid)
        )


def _next_session_number(db: Session, subscription_id: int) -> int:
    """Следующий порядковый номер сессии в рамках подписки."""
    last = (
        db.query(Booking.session_number)
        .filter(
            Booking.subscription_id == subscription_id,
            Booking.deleted_at.is_(None),
            Booking.status.notin_([BookingStatus.CANCELLED, BookingStatus.SPECIALIST_CANCELLED]),
        )
        .order_by(Booking.session_number.desc())
        .first()
    )
    if last is None or last[0] is None:
        return 1
    return last[0] + 1


# ---------- read ----------

def get_booking_by_id(db: Session, booking_id: int, include_deleted: bool = False) -> Optional[Booking]:
    query = (
        db.query(Booking)
        .options(
            joinedload(Booking.client),
            joinedload(Booking.service),
            joinedload(Booking.specialist),
            joinedload(Booking.group),
            joinedload(Booking.subscription),
            joinedload(Booking.co_specialists),
        )
        .filter(Booking.id == booking_id)
    )
    if not include_deleted:
        query = query.filter(Booking.deleted_at.is_(None))
    return query.first()


def get_bookings_in_range(
    db: Session,
    start: datetime,
    end: datetime,
    specialist_id: Optional[int] = None,
    client_id: Optional[int] = None,
) -> List[Booking]:
    query = (
        db.query(Booking)
        .options(
            joinedload(Booking.client),
            joinedload(Booking.service),
            joinedload(Booking.specialist),
            joinedload(Booking.group),
            joinedload(Booking.subscription),
            joinedload(Booking.co_specialists),
        )
        .filter(
            Booking.deleted_at.is_(None),
            Booking.start_time >= start,
            Booking.start_time < end,
        )
    )
    if specialist_id is not None:
        # Фильтр и по основному, и по со-ведущим
        query = query.filter(
            or_(
                Booking.specialist_id == specialist_id,
                Booking.co_specialists.any(GlobalUser.id == specialist_id),
            )
        )
    if client_id is not None:
        query = query.filter(Booking.client_id == client_id)
    return query.order_by(Booking.start_time).all()


# ---------- create ----------

def create_booking(db: Session, payload: BookingCreate) -> Booking:
    """Создаёт бронь с полной валидацией."""
    # 1. Загружаем подписку с её сервисом
    subscription = (
        db.query(ClientSubscription)
        .options(joinedload(ClientSubscription.service))
        .filter(ClientSubscription.id == payload.subscription_id)
        .first()
    )
    if not subscription:
        raise SubscriptionNotFound(f"Подписка {payload.subscription_id} не найдена")
    if subscription.deleted_at is not None or subscription.status != SubscriptionStatus.ACTIVE:
        raise SubscriptionNotActive(f"Абонемент не активен (status={subscription.status.value})")
    if subscription.used_sessions >= subscription.total_sessions:
        raise SubscriptionExhausted("Все сессии абонемента уже использованы")

    service = subscription.service

    # 2. Определяем тип брони и основного специалиста
    if service.is_group:
        booking_type = BookingType.GROUP
        # Для group основной ведущий должен быть передан явно
        if payload.specialist_id is None:
            raise InvalidSubscriptionConfig(
                "Для группового занятия укажите основного ведущего (specialist_id)"
            )
        specialist_id = payload.specialist_id
    else:
        booking_type = BookingType.INDIVIDUAL
        # Для individual специалист берётся из подписки, если не передан
        specialist_id = payload.specialist_id or subscription.assigned_specialist_id
        if specialist_id is None:
            raise InvalidSubscriptionConfig(
                "Для индивидуальной брони не определён специалист"
            )

    # 3. Валидация времени
    if payload.end_time <= payload.start_time:
        raise InvalidSubscriptionConfig("end_time должен быть позже start_time")

    # 4. Weekly limit
    _check_weekly_limit(db, subscription, payload.start_time)

    # 5. Конфликт времени специалиста
    if _has_specialist_conflict(db, specialist_id, payload.start_time, payload.end_time):
        raise TimeSlotConflict("Это время у специалиста уже занято")

    # 6. Создаём бронь
    booking = Booking(
        client_id=subscription.client_id,
        subscription_id=subscription.id,
        service_id=service.id,
        specialist_id=specialist_id,
        group_id=subscription.group_id if booking_type == BookingType.GROUP else None,
        start_time=payload.start_time,
        end_time=payload.end_time,
        booking_type=booking_type,
        status=BookingStatus.SCHEDULED,
        notes=payload.notes,
        is_recurring=False,
        session_number=_next_session_number(db, subscription.id),
    )
    db.add(booking)
    db.flush()  # получаем booking.id

    # 7. Со-ведущие (только для group)
    if booking_type == BookingType.GROUP:
        _set_co_specialists(db, booking, payload.co_specialist_ids or [])

    # 8. Декрементим счётчик подписки
    _bump_used_sessions(db, subscription, +1)

    db.commit()
    db.refresh(booking)
    return booking


# ---------- update ----------

def update_booking(db: Session, booking_id: int, payload: BookingUpdate) -> Optional[Booking]:
    booking = (
        db.query(Booking)
        .options(joinedload(Booking.subscription).joinedload(ClientSubscription.service))
        .filter(Booking.id == booking_id, Booking.deleted_at.is_(None))
        .first()
    )
    if not booking:
        return None

    old_status = booking.status

    new_start = payload.start_time or booking.start_time
    new_end = payload.end_time or booking.end_time
    new_specialist_id = payload.specialist_id or booking.specialist_id

    # Если время или специалист меняются — перепроверяем конфликты
    time_or_spec_changed = (
        payload.start_time is not None
        or payload.end_time is not None
        or payload.specialist_id is not None
    )
    if time_or_spec_changed:
        if new_end <= new_start:
            raise InvalidSubscriptionConfig("end_time должен быть позже start_time")

        if booking.subscription is not None:
            _check_weekly_limit(
                db, booking.subscription, new_start, exclude_booking_id=booking.id
            )
        if _has_specialist_conflict(
            db, new_specialist_id, new_start, new_end, exclude_booking_id=booking.id
        ):
            raise TimeSlotConflict("Это время у специалиста уже занято")

    # Применяем изменения
    if payload.start_time is not None:
        booking.start_time = payload.start_time
    if payload.end_time is not None:
        booking.end_time = payload.end_time
    if payload.specialist_id is not None:
        booking.specialist_id = payload.specialist_id
    if payload.notes is not None:
        booking.notes = payload.notes
    if payload.status is not None:
        booking.status = payload.status

    # Со-ведущие
    if payload.co_specialist_ids is not None and booking.booking_type == BookingType.GROUP:
        db.flush()
        _set_co_specialists(db, booking, payload.co_specialist_ids)

    # Реакция на смену статуса: возвращаем сессию при cancel, не меняем при missed/completed
    if (
        booking.subscription is not None
        and old_status != booking.status
    ):
        cancelled_states = {BookingStatus.CANCELLED, BookingStatus.SPECIALIST_CANCELLED}
        was_cancelled = old_status in cancelled_states
        is_cancelled = booking.status in cancelled_states

        if not was_cancelled and is_cancelled:
            # бронь стала отменённой — возвращаем сессию
            _bump_used_sessions(db, booking.subscription, -1)
            booking.cancelled_at = datetime.now(timezone.utc)
        elif was_cancelled and not is_cancelled:
            # отмена снята — снова списываем сессию (после повторной проверки лимитов выше)
            _bump_used_sessions(db, booking.subscription, +1)
            booking.cancelled_at = None

        if booking.status == BookingStatus.COMPLETED and booking.completed_at is None:
            booking.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(booking)
    return booking


# ---------- delete ----------

def delete_booking(db: Session, booking_id: int, actor_id: Optional[int] = None) -> bool:
    """
    Soft-delete: помечает deleted_at, возвращает сессию в подписку
    (если бронь была активной).
    """
    booking = (
        db.query(Booking)
        .options(joinedload(Booking.subscription))
        .filter(Booking.id == booking_id, Booking.deleted_at.is_(None))
        .first()
    )
    if not booking:
        return False

    was_active = booking.status not in {
        BookingStatus.CANCELLED, BookingStatus.SPECIALIST_CANCELLED, BookingStatus.MISSED,
    }
    booking.deleted_at = datetime.now(timezone.utc)
    if actor_id is not None:
        booking.cancelled_by = actor_id

    if was_active and booking.subscription is not None:
        _bump_used_sessions(db, booking.subscription, -1)

    db.commit()
    return True
