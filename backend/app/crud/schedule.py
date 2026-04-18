from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timedelta, timezone
from typing import Optional, List
import uuid
from app.models.schedule import Schedule
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate

def get_schedules_by_date(db: Session, date: datetime, user_id: Optional[int] = None, include_deleted: bool = False) -> List[Schedule]:
    query = db.query(Schedule).options(joinedload(Schedule.global_user)).filter(
        Schedule.start_time >= date,
        Schedule.start_time < date + timedelta(days=1)
    )

    if user_id:
        query = query.filter(Schedule.global_user_id == user_id)

    if not include_deleted:
        query = query.filter(Schedule.deleted_at.is_(None))

    return query.order_by(Schedule.start_time).all()

def get_schedule_by_id(db: Session, schedule_id: int, include_deleted: bool = False) -> Optional[Schedule]:
    query = db.query(Schedule).filter(Schedule.id == schedule_id)
    if not include_deleted:
        query = query.filter(Schedule.deleted_at.is_(None))
    return query.first()

def create_schedule(db: Session, schedule: ScheduleCreate) -> Schedule:
    db_schedule = Schedule(**schedule.dict())
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule

def update_schedule(db: Session, schedule_id: int, schedule_update: ScheduleUpdate) -> Optional[Schedule]:
    db_schedule = get_schedule_by_id(db, schedule_id)
    if db_schedule:
        update_data = schedule_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_schedule, field, value)
        db_schedule.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(db_schedule)
    return db_schedule

def delete_schedule(db: Session, schedule_id: int) -> bool:
    db_schedule = get_schedule_by_id(db, schedule_id)
    if db_schedule:
        db_schedule.deleted_at = datetime.now(timezone.utc)
        db.commit()
        return True
    return False

def get_schedules_by_user_and_time_range(db: Session, user_id: int, start_time: datetime, end_time: datetime) -> List[Schedule]:
    return db.query(Schedule).filter(
        Schedule.global_user_id == user_id,
        Schedule.start_time < end_time,
        Schedule.end_time > start_time,
        Schedule.deleted_at.is_(None)
    ).all()

def get_schedules_in_time_range(db: Session, start_time: datetime, end_time: datetime, user_id: Optional[int] = None) -> List[Schedule]:
    query = db.query(Schedule).options(joinedload(Schedule.global_user)).filter(
        Schedule.start_time < end_time,
        Schedule.end_time > start_time,
        Schedule.deleted_at.is_(None)
    )
    if user_id:
        query = query.filter(Schedule.global_user_id == user_id)
    return query.order_by(Schedule.start_time).all()

def get_schedules_by_recurrence_group(db: Session, recurrence_group_id: str, include_deleted: bool = False) -> List[Schedule]:
    query = db.query(Schedule).filter(Schedule.recurrence_group_id == recurrence_group_id)
    if not include_deleted:
        query = query.filter(Schedule.deleted_at.is_(None))
    return query.order_by(Schedule.start_time).all()

def create_recurring_schedules(db: Session, schedule: ScheduleCreate, weeks_ahead: int = 52) -> List[Schedule]:
    schedules = []
    recurrence_group_id = str(uuid.uuid4())

    for week in range(weeks_ahead):
        new_start_time = schedule.start_time + timedelta(weeks=week)
        new_end_time = schedule.end_time + timedelta(weeks=week)

        db_schedule = Schedule(
            global_user_id=schedule.global_user_id,
            title=schedule.title,
            description=schedule.description,
            start_time=new_start_time,
            end_time=new_end_time,
            recurrence_group_id=recurrence_group_id,
            is_recurring=True
        )
        db.add(db_schedule)
        schedules.append(db_schedule)

    db.commit()

    for db_schedule in schedules:
        db.refresh(db_schedule)

    return schedules

def update_recurring_series(db: Session, recurrence_group_id: str, schedule_update: ScheduleUpdate) -> List[Schedule]:
    schedules = get_schedules_by_recurrence_group(db, recurrence_group_id)

    updated_schedules = []
    for db_schedule in schedules:
        for field, value in schedule_update.dict(exclude_unset=True).items():
            if field in ['start_time', 'end_time']:
                continue
            setattr(db_schedule, field, value)
        db_schedule.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(db_schedule)
        updated_schedules.append(db_schedule)

    return updated_schedules

def delete_recurring_series(db: Session, recurrence_group_id: str, from_date: Optional[datetime] = None) -> bool:
    schedules = get_schedules_by_recurrence_group(db, recurrence_group_id)

    for db_schedule in schedules:
        if from_date:
            if db_schedule.start_time >= from_date:
                db_schedule.deleted_at = datetime.now(timezone.utc)
        else:
            db_schedule.deleted_at = datetime.now(timezone.utc)

    db.commit()
    return True

def move_recurring_series(db: Session, recurrence_group_id: str, new_start_time: datetime, new_end_time: datetime, from_date: Optional[datetime] = None) -> List[Schedule]:
    schedules = get_schedules_by_recurrence_group(db, recurrence_group_id)

    moved_schedules = []
    for db_schedule in schedules:
        if from_date:
            if db_schedule.start_time < from_date:
                continue

        time_offset = new_start_time - db_schedule.start_time
        db_schedule.start_time = db_schedule.start_time + time_offset
        db_schedule.end_time = db_schedule.end_time + time_offset
        db_schedule.updated_at = datetime.now(timezone.utc)
        moved_schedules.append(db_schedule)

    db.commit()
    for db_schedule in moved_schedules:
        db.refresh(db_schedule)

    return moved_schedules
