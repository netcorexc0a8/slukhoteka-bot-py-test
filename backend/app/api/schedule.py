from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate, ScheduleResponse
from app.crud.schedule import (
    get_schedules_by_date, create_schedule, update_schedule,
    delete_schedule, get_schedule_by_id, get_schedules_in_time_range,
    create_recurring_schedules, update_recurring_series, delete_recurring_series,
    get_schedules_by_recurrence_group, move_recurring_series,
    get_schedules_by_user_and_time_range
)
from app.models.user import GlobalUser

router = APIRouter()

@router.get("", response_model=list[ScheduleResponse])
def get_schedules(
    date: str = Query(..., description="Дата в формате YYYY-MM-DD"),
    user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    try:
        parsed_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат даты. Используйте YYYY-MM-DD"
        )

    schedules = get_schedules_by_date(db, parsed_date, user_id)

    result = []
    for s in schedules:
        schedule_dict = s.__dict__.copy()
        if '_sa_instance_state' in schedule_dict:
            del schedule_dict['_sa_instance_state']
        schedule_dict['user_name'] = s.global_user.name if s.global_user else None
        result.append(ScheduleResponse(**schedule_dict))

    return result

@router.get("/range", response_model=list[ScheduleResponse])
def get_schedules_range(
    start_date: str = Query(..., description="Начальная дата в формате YYYY-MM-DD"),
    end_date: str = Query(..., description="Конечная дата в формате YYYY-MM-DD"),
    user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат даты. Используйте YYYY-MM-DD"
        )

    schedules = get_schedules_in_time_range(db, start, end, user_id)

    result = []
    for s in schedules:
        schedule_dict = s.__dict__.copy()
        if '_sa_instance_state' in schedule_dict:
            del schedule_dict['_sa_instance_state']
        schedule_dict['user_name'] = s.global_user.name if s.global_user else None
        result.append(ScheduleResponse(**schedule_dict))

    return result

@router.post("/recurring", response_model=list[ScheduleResponse], status_code=status.HTTP_201_CREATED)
def create_recurring_schedules_endpoint(schedule: ScheduleCreate, db: Session = Depends(get_db)):
    existing_schedules = get_schedules_in_time_range(
        db, schedule.start_time, schedule.end_time, user_id=schedule.global_user_id
    )
    if existing_schedules:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Это время уже занято"
        )

    schedules = create_recurring_schedules(db, schedule)

    result = []
    for s in schedules:
        schedule_dict = s.__dict__.copy()
        if '_sa_instance_state' in schedule_dict:
            del schedule_dict['_sa_instance_state']
        schedule_dict['user_name'] = s.global_user.name if s.global_user else None
        result.append(ScheduleResponse(**schedule_dict))

    return result

@router.put("/series/{recurrence_group_id}", response_model=list[ScheduleResponse])
def update_recurring_series_endpoint(
    recurrence_group_id: str,
    schedule_update: ScheduleUpdate,
    db: Session = Depends(get_db)
):
    schedules = update_recurring_series(db, recurrence_group_id, schedule_update)
    if not schedules:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Серия записей не найдена"
        )

    result = []
    for s in schedules:
        schedule_dict = s.__dict__.copy()
        if '_sa_instance_state' in schedule_dict:
            del schedule_dict['_sa_instance_state']
        schedule_dict['user_name'] = s.global_user.name if s.global_user else None
        result.append(ScheduleResponse(**schedule_dict))

    return result

@router.delete("/series/{recurrence_group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recurring_series_endpoint(
    recurrence_group_id: str,
    from_date: Optional[str] = Query(None, description="Удалять записи начиная с этой даты (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    parsed_from_date = None
    if from_date:
        try:
            parsed_from_date = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный формат даты. Используйте YYYY-MM-DD"
            )

    success = delete_recurring_series(db, recurrence_group_id, parsed_from_date)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Серия записей не найдена"
        )
    return None

@router.post("/series/{recurrence_group_id}/move", response_model=list[ScheduleResponse])
def move_recurring_series_endpoint(
    recurrence_group_id: str,
    new_start_time: str = Query(..., description="Новое время начала в формате YYYY-MM-DDTHH:MM:SS"),
    new_end_time: str = Query(..., description="Новое время окончания в формате YYYY-MM-DDTHH:MM:SS"),
    from_date: Optional[str] = Query(None, description="Перемещать записи начиная с этой даты (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    try:
        parsed_start_time = datetime.strptime(new_start_time, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        parsed_end_time = datetime.strptime(new_end_time, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат времени. Используйте YYYY-MM-DDTHH:MM:SS"
        )

    parsed_from_date = None
    if from_date:
        try:
            parsed_from_date = datetime.strptime(from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный формат даты. Используйте YYYY-MM-DD"
            )

    schedules = move_recurring_series(db, recurrence_group_id, parsed_start_time, parsed_end_time, parsed_from_date)
    if not schedules:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Серия записей не найдена или нет записей для перемещения"
        )

    result = []
    for s in schedules:
        schedule_dict = s.__dict__.copy()
        if '_sa_instance_state' in schedule_dict:
            del schedule_dict['_sa_instance_state']
        schedule_dict['user_name'] = s.global_user.name if s.global_user else None
        result.append(ScheduleResponse(**schedule_dict))

    return result

@router.get("/series/{recurrence_group_id}", response_model=list[ScheduleResponse])
def get_recurring_series_endpoint(recurrence_group_id: str, db: Session = Depends(get_db)):
    schedules = get_schedules_by_recurrence_group(db, recurrence_group_id)

    result = []
    for s in schedules:
        schedule_dict = s.__dict__.copy()
        if '_sa_instance_state' in schedule_dict:
            del schedule_dict['_sa_instance_state']
        schedule_dict['user_name'] = s.global_user.name if s.global_user else None
        result.append(ScheduleResponse(**schedule_dict))

    return result

@router.get("/{schedule_id}", response_model=ScheduleResponse)
def get_schedule(
    schedule_id: int,
    include_deleted: bool = Query(False, description="Включать удаленные записи"),
    db: Session = Depends(get_db)
):
    schedule = get_schedule_by_id(db, schedule_id, include_deleted)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись не найдена"
        )

    schedule_dict = schedule.__dict__.copy()
    if '_sa_instance_state' in schedule_dict:
        del schedule_dict['_sa_instance_state']
    schedule_dict['user_name'] = schedule.global_user.name if schedule.global_user else None
    return ScheduleResponse(**schedule_dict)

@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_single_schedule(schedule: ScheduleCreate, db: Session = Depends(get_db)):
    existing_schedules = get_schedules_by_user_and_time_range(
        db, schedule.global_user_id, schedule.start_time, schedule.end_time
    )
    if existing_schedules:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Это время уже занято"
        )

    db_schedule = create_schedule(db, schedule)

    schedule_dict = db_schedule.__dict__.copy()
    if '_sa_instance_state' in schedule_dict:
        del schedule_dict['_sa_instance_state']
    schedule_dict['user_name'] = db_schedule.global_user.name if db_schedule.global_user else None
    return ScheduleResponse(**schedule_dict)

@router.put("/{schedule_id}", response_model=ScheduleResponse)
def update_single_schedule(
    schedule_id: int,
    schedule_update: ScheduleUpdate,
    db: Session = Depends(get_db)
):
    schedule = update_schedule(db, schedule_id, schedule_update)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись не найдена"
        )

    schedule_dict = schedule.__dict__.copy()
    if '_sa_instance_state' in schedule_dict:
        del schedule_dict['_sa_instance_state']
    schedule_dict['user_name'] = schedule.global_user.name if schedule.global_user else None
    return ScheduleResponse(**schedule_dict)

@router.delete("/{schedule_id}")
def delete_schedule_endpoint(
    schedule_id: int,
    db: Session = Depends(get_db)
):
    success = delete_schedule(db, schedule_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Запись не найдена"
        )
    return {"success": True}
