from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import Doctor, DoctorSchedule
from app.schemas.doctor_schedule import (
    DoctorScheduleCreate,
    DoctorScheduleResponse
)


router = APIRouter(
    prefix="/doctor-schedules",
    tags=["Doctor Schedules"]
)


@router.post(
    "",
    response_model=DoctorScheduleResponse
)
def create_schedule(
    schedule: DoctorScheduleCreate,
    db: Session = Depends(get_db)
):

    doctor = db.query(Doctor).filter(
        Doctor.id == schedule.doctor_id
    ).first()

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    new_schedule = DoctorSchedule(
        doctor_id=schedule.doctor_id,
        weekday=schedule.weekday,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        slot_duration=schedule.slot_duration,
        capacity=schedule.capacity,
        is_active=schedule.is_active
    )

    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)

    return new_schedule


@router.get(
    "",
    response_model=list[DoctorScheduleResponse]
)
def get_schedules(
    db: Session = Depends(get_db)
):

    return db.query(DoctorSchedule).all()


@router.get(
    "/doctor/{doctor_id}",
    response_model=list[DoctorScheduleResponse]
)
def get_doctor_schedules(
    doctor_id: int,
    db: Session = Depends(get_db)
):

    doctor = db.query(Doctor).filter(
        Doctor.id == doctor_id
    ).first()

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    return db.query(DoctorSchedule).filter(
        DoctorSchedule.doctor_id == doctor_id
    ).all()