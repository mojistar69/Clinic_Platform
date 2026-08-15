from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import Doctor
from app.schemas.doctor import DoctorCreate, DoctorResponse
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import Doctor, DoctorSchedule
from app.schemas.doctor_schedule import DoctorScheduleResponse
from app.models.models import DoctorSchedule
from app.schemas.doctor_schedule import DoctorScheduleResponse
router = APIRouter(
    prefix="/doctors",
    tags=["Doctors"]
)


@router.get(
    "/{doctor_id}/schedule",
    response_model=list[DoctorScheduleResponse]
)
def get_doctor_schedule(
    doctor_id: int,
    db: Session = Depends(get_db)
):
    # بررسی وجود پزشک
    doctor = db.query(Doctor).filter(
        Doctor.id == doctor_id
    ).first()

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    schedules = db.query(DoctorSchedule).filter(
        DoctorSchedule.doctor_id == doctor_id,
        DoctorSchedule.is_active == True
    ).order_by(
        DoctorSchedule.weekday
    ).all()

    return schedules

router = APIRouter(
    prefix="/doctors",
    tags=["Doctors"]
)


@router.post(
    "",
    response_model=DoctorResponse
)
def create_doctor(
    doctor: DoctorCreate,
    db: Session = Depends(get_db)
):

    new_doctor = Doctor(
        name=doctor.name,
        specialty=doctor.specialty,
        room_number=doctor.room_number,
        clinic_id=doctor.clinic_id
    )

    db.add(new_doctor)
    db.commit()
    db.refresh(new_doctor)

    return new_doctor


@router.get(
    "",
    response_model=list[DoctorResponse]
)
def get_doctors(
    db: Session = Depends(get_db)
):

    return db.query(Doctor).all()