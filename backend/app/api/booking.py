"""API записей на занятия (bookings)."""
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.booking import BookingCreate, BookingUpdate, BookingResponse
from app.crud.booking import (
    get_booking_by_id, get_bookings_in_range,
    create_booking, update_booking, delete_booking,
    create_recurring_bookings, move_group_session,
)
from app.services.exceptions import (
    SubscriptionNotFound, SubscriptionNotActive, SubscriptionExhausted,
    WeeklyLimitExceeded, TimeSlotConflict, InvalidSubscriptionConfig,
)

router = APIRouter()


class RecurringCreateRequest(BaseModel):
    subscription_id: int
    first_start_time: datetime
    duration_minutes: int = 60
    specialist_id: Optional[int] = None
    co_specialist_ids: Optional[List[int]] = None
    notes: Optional[str] = None


class RecurringCreateResponse(BaseModel):
    created: List[BookingResponse]
    failed: List[dict]


class GroupMoveRequest(BaseModel):
    group_id: str
    old_start: datetime
    new_start: datetime
    duration_minutes: Optional[int] = None


class GroupMoveResponse(BaseModel):
    moved: List[BookingResponse]
    failed: List[dict]


def _to_response(b) -> BookingResponse:
    co_specialists = list(b.co_specialists or [])
    return BookingResponse(
        id=b.id, client_id=b.client_id, subscription_id=b.subscription_id,
        service_id=b.service_id, specialist_id=b.specialist_id, group_id=b.group_id,
        start_time=b.start_time, end_time=b.end_time,
        booking_type=b.booking_type, status=b.status,
        notes=b.notes, is_recurring=b.is_recurring,
        recurrence_group_id=b.recurrence_group_id, session_number=b.session_number,
        created_at=b.created_at, updated_at=b.updated_at,
        deleted_at=b.deleted_at, completed_at=b.completed_at,
        cancelled_at=b.cancelled_at, cancelled_by=b.cancelled_by,
        client_name=b.client.name if b.client else None,
        client_phone=b.client.phone if b.client else None,
        specialist_name=b.specialist.name if b.specialist else None,
        service_name=b.service.name if b.service else None,
        group_name=b.group.name if b.group else None,
        co_specialist_ids=[s.id for s in co_specialists],
        co_specialist_names=[s.name for s in co_specialists if s.name],
        subscription_total=b.subscription.total_sessions if b.subscription else None,
        subscription_used=b.subscription.used_sessions if b.subscription else None,
        subscription_remaining=(
            b.subscription.remaining_sessions if b.subscription else None
        ),
    )


def _domain_error_to_http(exc: Exception) -> HTTPException:
    if isinstance(exc, SubscriptionNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, (WeeklyLimitExceeded, TimeSlotConflict)):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, (SubscriptionNotActive, SubscriptionExhausted, InvalidSubscriptionConfig)):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


@router.get("", response_model=List[BookingResponse])
def list_bookings(
    date: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    specialist_id: Optional[int] = None,
    client_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    if date is not None:
        try:
            d = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат даты")
        start, end = d, d + timedelta(days=1)
    elif start_date and end_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            end = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат даты")
    else:
        raise HTTPException(status_code=400, detail="Укажите date или (start_date и end_date)")
    bookings = get_bookings_in_range(
        db, start, end, specialist_id=specialist_id, client_id=client_id
    )
    return [_to_response(b) for b in bookings]


@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking_endpoint(booking_id: int, db: Session = Depends(get_db)):
    b = get_booking_by_id(db, booking_id)
    if not b:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    return _to_response(b)


@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking_endpoint(payload: BookingCreate, db: Session = Depends(get_db)):
    try:
        booking = create_booking(db, payload)
    except (SubscriptionNotFound, SubscriptionNotActive, SubscriptionExhausted,
            WeeklyLimitExceeded, TimeSlotConflict, InvalidSubscriptionConfig) as e:
        raise _domain_error_to_http(e)
    return _to_response(get_booking_by_id(db, booking.id))


@router.post("/recurring", response_model=RecurringCreateResponse, status_code=status.HTTP_201_CREATED)
def create_recurring_endpoint(payload: RecurringCreateRequest, db: Session = Depends(get_db)):
    try:
        created, failed = create_recurring_bookings(
            db,
            subscription_id=payload.subscription_id,
            first_start_time=payload.first_start_time,
            duration_minutes=payload.duration_minutes,
            specialist_id=payload.specialist_id,
            co_specialist_ids=payload.co_specialist_ids,
            notes=payload.notes,
        )
    except (SubscriptionNotFound, SubscriptionNotActive, SubscriptionExhausted,
            InvalidSubscriptionConfig) as e:
        raise _domain_error_to_http(e)
    created_full = [get_booking_by_id(db, b.id) for b in created]
    return RecurringCreateResponse(
        created=[_to_response(b) for b in created_full],
        failed=[{"date": d.isoformat(), "reason": r} for d, r in failed],
    )


@router.put("/{booking_id}", response_model=BookingResponse)
def update_booking_endpoint(
    booking_id: int, payload: BookingUpdate, db: Session = Depends(get_db),
):
    try:
        booking = update_booking(db, booking_id, payload)
    except (WeeklyLimitExceeded, TimeSlotConflict, InvalidSubscriptionConfig) as e:
        raise _domain_error_to_http(e)
    if not booking:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    return _to_response(get_booking_by_id(db, booking.id))


@router.post("/group/move", response_model=GroupMoveResponse)
def move_group_endpoint(payload: GroupMoveRequest, db: Session = Depends(get_db)):
    try:
        moved, failed = move_group_session(
            db,
            group_id=payload.group_id,
            old_start=payload.old_start,
            new_start=payload.new_start,
            duration_minutes=payload.duration_minutes,
        )
    except (TimeSlotConflict, InvalidSubscriptionConfig, WeeklyLimitExceeded) as e:
        raise _domain_error_to_http(e)
    moved_full = [get_booking_by_id(db, b.id) for b in moved]
    return GroupMoveResponse(
        moved=[_to_response(b) for b in moved_full],
        failed=[{"client": c, "reason": r} for c, r in failed],
    )


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_booking_endpoint(
    booking_id: int,
    actor_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    if not delete_booking(db, booking_id, actor_id=actor_id):
        raise HTTPException(status_code=404, detail="Запись не найдена")
    return None