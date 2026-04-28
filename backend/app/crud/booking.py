"""
CRUD для броней (Booking).
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Tuple

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
    new_booking_type: Optional[BookingType] = None,
    new_group_id: Optional[str] = None,
    exclude_booking_id: Optional[int] = None,
) -> bool:
    """
    Если новая бронь — групповая того же group_id и start_time, что и существующая,
    это одно и то же занятие, не конфликт.
    """
    query = db.query(Booking).filter(
        Booking.specialist_id == specialist_id,
        Booking.deleted_at.is_(None),
        Booking.status.notin_([BookingStatus.CANCELLED, BookingStatus.SPECIALIST_CANCELLED]),
        Booking.start_time < end_time,
        Booking.end_time > start_time,
    )
    if exclude_booking_id is not None:
        query = query.filter(Booking.id != exclude_booking_id)

    if new_booking_type == BookingType.GROUP and new_group_id is not None:
        query = query.filter(
            ~and_(
                Booking.group_id == new_group_id,
                Booking.start_time == start_time,
                Booking.booking_type == BookingType.GROUP,
            )
        )
    return db.query(query.exists()).scalar()


def _check_weekly_limit(
    db: Session,
    subscription: ClientSubscription,
    start_time: datetime,
    exclude_booking_id: Optional[int] = None,
) -> None:
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
    new_used = max(0, min(subscription.total_sessions, subscription.used_sessions + delta))
    subscription.used_sessions = new_used
    if new_used >= subscription.total_sessions:
        subscription.status = SubscriptionStatus.COMPLETED
    elif subscription.status == SubscriptionStatus.COMPLETED and new_used < subscription.total_sessions:
        subscription.status = SubscriptionStatus.ACTIVE


def _set_co_specialists(db: Session, booking: Booking, specialist_ids: List[int]) -> None:
    db.execute(
        booking_specialists.delete().where(booking_specialists.c.booking_id == booking.id)
    )
    ids = set(specialist_ids or [])
    ids.add(booking.specialist_id)
    for sid in ids:
        db.execute(
            booking_specialists.insert().values(booking_id=booking.id, specialist_id=sid)
        )


def _next_session_number(db: Session, subscription_id: int) -> int:
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

def _validate_and_resolve(
    db: Session, payload: BookingCreate,
) -> Tuple[ClientSubscription, BookingType, int, Optional[str]]:
    """Общая часть валидации, возвращает (subscription, booking_type, specialist_id, group_id)."""
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

    service = subscription.service
    if service.is_group:
        booking_type = BookingType.GROUP
        if payload.specialist_id is None:
            raise InvalidSubscriptionConfig(
                "Для группового занятия укажите основного ведущего (specialist_id)"
            )
        specialist_id = payload.specialist_id
        new_group_id = subscription.group_id
    else:
        booking_type = BookingType.INDIVIDUAL
        specialist_id = payload.specialist_id or subscription.assigned_specialist_id
        if specialist_id is None:
            raise InvalidSubscriptionConfig(
                "Для индивидуальной брони не определён специалист"
            )
        new_group_id = None

    if payload.end_time <= payload.start_time:
        raise InvalidSubscriptionConfig("end_time должен быть позже start_time")

    return subscription, booking_type, specialist_id, new_group_id


def create_booking(db: Session, payload: BookingCreate) -> Booking:
    subscription, booking_type, specialist_id, new_group_id = _validate_and_resolve(db, payload)
    if subscription.used_sessions >= subscription.total_sessions:
        raise SubscriptionExhausted("Все сессии абонемента уже использованы")

    _check_weekly_limit(db, subscription, payload.start_time)
    if _has_specialist_conflict(
        db, specialist_id, payload.start_time, payload.end_time,
        new_booking_type=booking_type,
        new_group_id=new_group_id,
    ):
        raise TimeSlotConflict("Это время у специалиста уже занято")

    booking = Booking(
        client_id=subscription.client_id,
        subscription_id=subscription.id,
        service_id=subscription.service_id,
        specialist_id=specialist_id,
        group_id=new_group_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        booking_type=booking_type,
        status=BookingStatus.SCHEDULED,
        notes=payload.notes,
        is_recurring=False,
        session_number=_next_session_number(db, subscription.id),
    )
    db.add(booking)
    db.flush()

    if booking_type == BookingType.GROUP:
        _set_co_specialists(db, booking, payload.co_specialist_ids or [])

    _bump_used_sessions(db, subscription, +1)

    db.commit()
    db.refresh(booking)
    return booking


# ---------- recurring ----------

def create_recurring_bookings(
    db: Session,
    *,
    subscription_id: int,
    first_start_time: datetime,
    duration_minutes: int = 60,
    specialist_id: Optional[int] = None,
    co_specialist_ids: Optional[List[int]] = None,
    notes: Optional[str] = None,
) -> Tuple[List[Booking], List[Tuple[datetime, str]]]:
    """
    Создаёт серию броней — по одной в неделю, начиная с first_start_time,
    столько штук, сколько осталось сессий в абонементе.

    Возвращает (created_bookings, failed_dates_with_reasons).
    Если все сессии не помещаются (конфликты) — создадутся те, что смогли.
    """
    subscription = (
        db.query(ClientSubscription)
        .options(joinedload(ClientSubscription.service))
        .filter(ClientSubscription.id == subscription_id)
        .first()
    )
    if not subscription:
        raise SubscriptionNotFound(f"Подписка {subscription_id} не найдена")
    if subscription.deleted_at is not None or subscription.status != SubscriptionStatus.ACTIVE:
        raise SubscriptionNotActive(f"Абонемент не активен")

    service = subscription.service
    remaining = subscription.total_sessions - subscription.used_sessions
    if remaining <= 0:
        raise SubscriptionExhausted("Все сессии абонемента уже использованы")

    if service.is_group:
        if specialist_id is None:
            raise InvalidSubscriptionConfig(
                "Для группового занятия укажите основного ведущего"
            )
        booking_type = BookingType.GROUP
        new_group_id = subscription.group_id
    else:
        booking_type = BookingType.INDIVIDUAL
        specialist_id = specialist_id or subscription.assigned_specialist_id
        if specialist_id is None:
            raise InvalidSubscriptionConfig("Не определён специалист")
        new_group_id = None

    created: List[Booking] = []
    failed: List[Tuple[datetime, str]] = []

    for i in range(remaining):
        start = first_start_time + timedelta(weeks=i)
        end = start + timedelta(minutes=duration_minutes)

        # weekly_limit проверка не нужна — мы по одной в неделю и так
        # (для service.weekly_limit=True)
        try:
            if _has_specialist_conflict(
                db, specialist_id, start, end,
                new_booking_type=booking_type,
                new_group_id=new_group_id,
            ):
                failed.append((start, "время у специалиста занято"))
                continue
            if not service.weekly_limit:
                # Если правила недели нет — норм.
                pass
            else:
                # Проверяем, что в этой неделе ещё нет брони этого абонемента
                # (например, ранее уже была создана вручную)
                _check_weekly_limit(db, subscription, start)
        except WeeklyLimitExceeded as e:
            failed.append((start, str(e)))
            continue

        booking = Booking(
            client_id=subscription.client_id,
            subscription_id=subscription.id,
            service_id=service.id,
            specialist_id=specialist_id,
            group_id=new_group_id,
            start_time=start,
            end_time=end,
            booking_type=booking_type,
            status=BookingStatus.SCHEDULED,
            notes=notes,
            is_recurring=True,
            recurrence_group_id=None,  # проставим после flush
            session_number=_next_session_number(db, subscription.id),
        )
        db.add(booking)
        db.flush()
        if booking_type == BookingType.GROUP:
            _set_co_specialists(db, booking, co_specialist_ids or [])
        _bump_used_sessions(db, subscription, +1)
        created.append(booking)

    # Объединяем все созданные одной серией
    if created:
        rec_id = str(uuid.uuid4())
        for b in created:
            b.recurrence_group_id = rec_id

    db.commit()
    for b in created:
        db.refresh(b)
    return created, failed


# ---------- update / move ----------

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
            db, new_specialist_id, new_start, new_end,
            new_booking_type=booking.booking_type,
            new_group_id=booking.group_id,
            exclude_booking_id=booking.id,
        ):
            raise TimeSlotConflict("Это время у специалиста уже занято")

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

    if payload.co_specialist_ids is not None and booking.booking_type == BookingType.GROUP:
        db.flush()
        _set_co_specialists(db, booking, payload.co_specialist_ids)

    if booking.subscription is not None and old_status != booking.status:
        cancelled_states = {BookingStatus.CANCELLED, BookingStatus.SPECIALIST_CANCELLED}
        was_cancelled = old_status in cancelled_states
        is_cancelled = booking.status in cancelled_states
        if not was_cancelled and is_cancelled:
            _bump_used_sessions(db, booking.subscription, -1)
            booking.cancelled_at = datetime.now(timezone.utc)
        elif was_cancelled and not is_cancelled:
            _bump_used_sessions(db, booking.subscription, +1)
            booking.cancelled_at = None
        if booking.status == BookingStatus.COMPLETED and booking.completed_at is None:
            booking.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(booking)
    return booking


def move_group_session(
    db: Session,
    *,
    group_id: str,
    old_start: datetime,
    new_start: datetime,
    duration_minutes: Optional[int] = None,
) -> Tuple[List[Booking], List[Tuple[str, str]]]:
    """
    Переносит ВСЁ групповое занятие (все брони с (group_id, start_time=old_start))
    на новое время. Длительность сохраняется, либо берётся из duration_minutes.
    Возвращает (moved, failed_clients_with_reasons).
    """
    bookings = (
        db.query(Booking)
        .options(
            joinedload(Booking.client),
            joinedload(Booking.subscription).joinedload(ClientSubscription.service),
        )
        .filter(
            Booking.group_id == group_id,
            Booking.start_time == old_start,
            Booking.booking_type == BookingType.GROUP,
            Booking.deleted_at.is_(None),
            Booking.status.notin_([BookingStatus.CANCELLED, BookingStatus.SPECIALIST_CANCELLED]),
        )
        .all()
    )
    if not bookings:
        return [], []

    sample = bookings[0]
    delta = new_start - old_start
    moved: List[Booking] = []
    failed: List[Tuple[str, str]] = []

    # Проверяем конфликт основного ведущего (один на всех — общий слот занятия)
    new_end_sample = new_start + (sample.end_time - sample.start_time)
    if duration_minutes is not None:
        new_end_sample = new_start + timedelta(minutes=duration_minutes)
    if _has_specialist_conflict(
        db, sample.specialist_id, new_start, new_end_sample,
        new_booking_type=BookingType.GROUP,
        new_group_id=group_id,
    ):
        # Этот конфликт говорит про "что-то ДРУГОЕ" в это время —
        # т.к. фильтр исключает брони того же group_id+start. Но мы переносим на new_start,
        # поэтому фильтр не сработает и конфликт реальный.
        raise TimeSlotConflict("Новое время у ведущего уже занято")

    for b in bookings:
        new_b_start = b.start_time + delta
        new_b_end = (
            new_b_start + timedelta(minutes=duration_minutes)
            if duration_minutes is not None else b.end_time + delta
        )
        try:
            if b.subscription is not None:
                _check_weekly_limit(
                    db, b.subscription, new_b_start, exclude_booking_id=b.id,
                )
            b.start_time = new_b_start
            b.end_time = new_b_end
            moved.append(b)
        except WeeklyLimitExceeded as e:
            failed.append((b.client.name if b.client else f"id={b.client_id}", str(e)))

    db.commit()
    for b in moved:
        db.refresh(b)
    return moved, failed


# ---------- delete ----------

def delete_booking(db: Session, booking_id: int, actor_id: Optional[int] = None) -> bool:
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